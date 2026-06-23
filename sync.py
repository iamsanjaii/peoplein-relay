import os
import time
import json
import pyodbc
import requests
from datetime import datetime
import threading

# --- CONFIGURATION ---
# IMPORTANT: Update these values to match your Windows laptop!
API_URL = "https://apiclients.captlnpeople.com"
API_KEY = "YOUR_API_KEY_HERE"
MACHINE_NAME = "Relay-Python-1"
MDB_PATH = r"C:\Program Files (x86)\eSSL\eTimeTrackLite\eTimeTrackLite1.mdb"
SYNC_INTERVAL_MINUTES = 5

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"lastAttendanceLogId": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_heartbeat():
    while True:
        try:
            url = f"{API_URL}/api/v1/relay/heartbeat"
            headers = {
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "version": "1.0.0-python",
                "machineName": MACHINE_NAME
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat sent successfully.")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat failed: {response.text}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat error: {e}")
        
        # Run every 60 seconds
        time.sleep(60)

def sync_attendance():
    while True:
        try:
            state = load_state()
            last_id = state["lastAttendanceLogId"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting sync from Log ID: {last_id}")

            conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={MDB_PATH};"
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            first_of_month_str = datetime.now().strftime("%Y-%m-01")
            
            # Using MS Access specific date literal syntax #YYYY-MM-DD#
            query = f"""
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
                  AND a.AttendanceDate >= #{first_of_month_str}#
                ORDER BY a.attendanceLogId ASC
            """

            cursor.execute(query, last_id)
            rows = cursor.fetchall()

            if not rows:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No new records to sync.")
                conn.close()
            else:
                records_payload = []
                new_max_id = last_id

                for row in rows:
                    log_id = row[0]
                    emp_code = str(row[1]) if row[1] is not None else ""
                    
                    # Parse dates safely
                    att_date = row[2].strftime("%Y-%m-%d") if row[2] else ""
                    in_time = row[3].strftime("%Y-%m-%dT%H:%M:%S") + "Z" if row[3] else None
                    out_time = row[4].strftime("%Y-%m-%dT%H:%M:%S") + "Z" if row[4] else None
                    
                    duration = int(row[5]) if row[5] is not None else 0
                    late_by = int(row[6]) if row[6] is not None else 0
                    early_by = int(row[7]) if row[7] is not None else 0

                    if log_id > new_max_id:
                        new_max_id = log_id

                    records_payload.append({
                        "employeeCode": emp_code,
                        "attendanceDate": att_date,
                        "checkIn": in_time,
                        "checkOut": out_time,
                        "workedMinutes": duration,
                        "lateMinutes": late_by,
                        "earlyExitMinutes": early_by
                    })

                conn.close()

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetched {len(records_payload)} records. Syncing to API...")

                url = f"{API_URL}/api/v1/relay/attendance/sync"
                headers = {
                    "X-API-Key": API_KEY,
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json={"records": records_payload}, headers=headers, timeout=30)
                
                if response.status_code in [200, 201]:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully synced {len(records_payload)} records. New Log ID: {new_max_id}")
                    state["lastAttendanceLogId"] = new_max_id
                    save_state(state)
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] API Sync Failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sync error: {e}")

        # Sleep for the configured interval
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping for {SYNC_INTERVAL_MINUTES} minutes...")
        time.sleep(SYNC_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    print("=========================================")
    print(" PeopleIN Relay - Headless Python Script")
    print("=========================================")
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Start sync loop in main thread
    sync_attendance()
