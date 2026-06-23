package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// Config represents the config.json structure
type Config struct {
	APIKey              string `json:"apiKey"`
	APIUrl              string `json:"apiUrl"`
	MDBPath             string `json:"mdbPath"`
	SyncIntervalMinutes int    `json:"syncIntervalMinutes"`
	MachineName         string `json:"machineName"`
}

// State represents the state.json structure
type State struct {
	LastAttendanceLogId int    `json:"lastAttendanceLogId"`
	LastSyncAt          string `json:"lastSyncAt"`
}

var (
	configPath = "config.json"
	statePath  = "C:\\ProgramData\\PeopleINRelay\\state.json"
)

func init() {
	// For local testing on mac/linux, fallback state path to local dir
	if os.Getenv("GOOS") != "windows" && os.PathSeparator != '\\' {
		statePath = "state.json"
	}
}

// LoadConfig reads config.json
func LoadConfig() (*Config, error) {
	file, err := os.Open(configPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var cfg Config
	if err := json.NewDecoder(file).Decode(&cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

// LoadState reads state.json
func LoadState() (*State, error) {
	file, err := os.Open(statePath)
	if err != nil {
		if os.IsNotExist(err) {
			return &State{LastAttendanceLogId: 0}, nil
		}
		return nil, err
	}
	defer file.Close()

	var state State
	if err := json.NewDecoder(file).Decode(&state); err != nil {
		return nil, err
	}
	return &state, nil
}

// SaveConfigStruct saves config.json
func SaveConfigStruct(cfg *Config) error {
	dir := filepath.Dir(configPath)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}

	file, err := os.Create(configPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(cfg)
}

// SaveState saves state.json
func SaveState(state *State) error {
	dir := filepath.Dir(statePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	file, err := os.Create(statePath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(state)
}
