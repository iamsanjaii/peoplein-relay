package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/alexbrainman/odbc"
)

// FetchIncrementalAttendance connects to the MDB and fetches new attendance records
func FetchIncrementalAttendance(mdbPath string, lastId int) ([]RelayAttendanceRecord, int, error) {
	connStr := fmt.Sprintf("Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;", mdbPath)
	db, err := sql.Open("odbc", connStr)
	if err != nil {
		return nil, 0, err
	}
	defer db.Close()

	// Get first day of current month as a string for MS Access
	now := time.Now()
	firstOfMonthStr := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, now.Location()).Format("2006-01-02")

	query := fmt.Sprintf(`
		SELECT TOP 500
			a.attendanceLogId, 
			e.EmployeeCode, 
			a.AttendanceDate, 
			a.InTime, 
			a.OutTime, 
			a.Duration, 
			a.LateBy, 
			a.EarlyBy
		FROM AttendanceLogs a
		INNER JOIN Employees e ON a.EmployeeId = e.EmployeeId
		WHERE a.attendanceLogId > ? 
		  AND a.AttendanceDate >= #%s#
		ORDER BY a.attendanceLogId ASC
	`, firstOfMonthStr)

	rows, err := db.Query(query, lastId)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var records []RelayAttendanceRecord
	var maxId int = lastId

	for rows.Next() {
		var logId int
		var empCode string
		var attDate time.Time
		var inTime, outTime sql.NullTime
		var duration, lateBy, earlyBy sql.NullInt64

		err := rows.Scan(&logId, &empCode, &attDate, &inTime, &outTime, &duration, &lateBy, &earlyBy)
		if err != nil {
			log.Printf("Failed to scan row: %v", err)
			continue
		}

		if logId > maxId {
			maxId = logId
		}

		var inStr, outStr *string
		if inTime.Valid {
			t := inTime.Time.Format(time.RFC3339)
			inStr = &t
		}
		if outTime.Valid {
			t := outTime.Time.Format(time.RFC3339)
			outStr = &t
		}

		records = append(records, RelayAttendanceRecord{
			EmployeeCode:     empCode,
			AttendanceDate:   attDate.Format("2006-01-02"),
			CheckIn:          inStr,
			CheckOut:         outStr,
			WorkedMinutes:    int(duration.Int64),
			LateMinutes:      int(lateBy.Int64),
			EarlyExitMinutes: int(earlyBy.Int64),
		})
	}

	return records, maxId, nil
}
