package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// RelayAttendanceRecord matches the backend RelayAttendanceRecord structure
type RelayAttendanceRecord struct {
	EmployeeCode     string  `json:"employeeCode"`
	AttendanceDate   string  `json:"attendanceDate"`
	CheckIn          *string `json:"checkIn"`
	CheckOut         *string `json:"checkOut"`
	WorkedMinutes    int     `json:"workedMinutes"`
	LateMinutes      int     `json:"lateMinutes"`
	EarlyExitMinutes int     `json:"earlyExitMinutes"`
}

// SendHeartbeat sends a heartbeat signal to the main server
func SendHeartbeat(serverURL string, apiKey string, machineName string) error {
	payload := map[string]string{
		"version":     "1.0.0",
		"machineName": machineName,
	}
	jsonData, _ := json.Marshal(payload)

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/relay/heartbeat", serverURL), bytes.NewBuffer(jsonData))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", apiKey)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("heartbeat failed with status: %d", resp.StatusCode)
	}

	return nil
}

// SendAttendanceSync sends the collected attendance records to the main server
func SendAttendanceSync(serverURL string, apiKey string, records []RelayAttendanceRecord) error {
	if len(records) == 0 {
		return nil
	}

	payload := map[string]interface{}{
		"records": records,
	}
	jsonData, _ := json.Marshal(payload)

	req, err := http.NewRequest("POST", fmt.Sprintf("%s/api/v1/relay/attendance/sync", serverURL), bytes.NewBuffer(jsonData))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", apiKey)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("sync failed with status: %d", resp.StatusCode)
	}

	return nil
}
