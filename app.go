package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/alexbrainman/odbc"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct
type App struct {
	ctx    context.Context
	ticker *time.Ticker
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) emitLog(msg string) {
	log.Println(msg)
	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, "log-update", msg)
	}
}

func (a *App) emitSyncUpdate(count int, errStr string) {
	if a.ctx != nil {
		runtime.EventsEmit(a.ctx, "sync-update", map[string]interface{}{
			"count": count,
			"error": errStr,
		})
	}
}

// QuitRelay shuts down the application
func (a *App) QuitRelay() {
	if a.ctx != nil {
		runtime.Quit(a.ctx)
	}
}

// GetConfig returns the current configuration
func (a *App) GetConfig() (*Config, error) {
	return LoadConfig()
}

// SaveConfig saves the given config
func (a *App) SaveConfig(cfg Config) error {
	return SaveConfigStruct(&cfg)
}

// GetState returns the current sync state
func (a *App) GetState() (*State, error) {
	return LoadState()
}

// TestDatabase connection and return stats
func (a *App) TestDatabase(mdbPath string) (map[string]interface{}, error) {
	connStr := fmt.Sprintf("Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;", mdbPath)
	db, err := sql.Open("odbc", connStr)
	if err != nil {
		return nil, fmt.Errorf("ODBC driver error: %v", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("Database connection failed: %v", err)
	}

	var empCount int
	err = db.QueryRow("SELECT COUNT(*) FROM Employees").Scan(&empCount)
	if err != nil {
		return nil, fmt.Errorf("Could not read Employees table: %v", err)
	}

	var attCount int
	err = db.QueryRow("SELECT COUNT(*) FROM AttendanceLogs").Scan(&attCount)
	if err != nil {
		return nil, fmt.Errorf("Could not read AttendanceLogs table: %v", err)
	}

	var latest string
	err = db.QueryRow("SELECT TOP 1 AttendanceDate FROM AttendanceLogs ORDER BY attendanceLogId DESC").Scan(&latest)
	if err != nil {
		latest = "Unknown"
	}

	return map[string]interface{}{
		"success":           true,
		"employeeCount":     empCount,
		"attendanceCount":   attCount,
		"latestAttendance":  latest,
	}, nil
}

// TestAPI connection and heartbeat
func (a *App) TestAPI(apiUrl string, apiKey string, machineName string) (map[string]interface{}, error) {
	err := SendHeartbeat(apiUrl, apiKey, machineName)
	if err != nil {
		return nil, fmt.Errorf("API Test Failed: %v", err)
	}
	return map[string]interface{}{"success": true}, nil
}

// StartSync starts the background polling loop
func (a *App) StartSync() error {
	cfg, err := LoadConfig()
	if err != nil {
		return err
	}
	state, err := LoadState()
	if err != nil {
		return err
	}

	// Initial sync immediately
	go a.performSync(cfg, state)

	if a.ticker != nil {
		a.ticker.Stop()
	}

	// Start Continuous Heartbeat (Every 1 minute)
	go func() {
		heartbeatTicker := time.NewTicker(1 * time.Minute)
		defer heartbeatTicker.Stop()
		for {
			err := SendHeartbeat(cfg.APIUrl, cfg.APIKey, cfg.MachineName)
			if err != nil {
				a.emitLog(fmt.Sprintf("Heartbeat failed: %v", err))
			} else {
				a.emitLog("Heartbeat sent successfully")
			}
			<-heartbeatTicker.C
		}
	}()

	interval := time.Duration(cfg.SyncIntervalMinutes) * time.Minute
	a.ticker = time.NewTicker(interval)

	go func() {
		for range a.ticker.C {
			// Update state from disk each tick just in case
			currentState, _ := LoadState()
			if currentState == nil {
				currentState = state
			}
			a.performSync(cfg, currentState)
		}
	}()

	return nil
}

func (a *App) performSync(cfg *Config, state *State) {
	a.emitLog(fmt.Sprintf("Starting incremental sync from Log ID: %d", state.LastAttendanceLogId))
	
	records, newMaxId, err := FetchIncrementalAttendance(cfg.MDBPath, state.LastAttendanceLogId)
	if err != nil {
		a.emitLog(fmt.Sprintf("Database read error: %v", err))
		a.emitSyncUpdate(0, err.Error())
		return
	}

	if len(records) == 0 {
		a.emitLog("No new records to sync.")
		a.emitSyncUpdate(0, "")
		return
	}

	a.emitLog(fmt.Sprintf("Fetched %d records. Syncing to PeopleIN...", len(records)))

	err = SendAttendanceSync(cfg.APIUrl, cfg.APIKey, records)
	if err != nil {
		a.emitLog(fmt.Sprintf("Failed to sync to PeopleIN API: %v", err))
		a.emitSyncUpdate(0, err.Error())
		return
	}

	state.LastAttendanceLogId = newMaxId
	state.LastSyncAt = time.Now().Format(time.RFC3339)
	
	_ = SaveState(state)
	
	a.emitLog(fmt.Sprintf("Successfully synced %d records. New Log ID: %d", len(records), newMaxId))
	a.emitSyncUpdate(len(records), "")
}
