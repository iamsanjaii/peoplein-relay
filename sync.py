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
API_KEY = ""
MACHINE_NAME = "Relay-Python-1"
MDB_PATH = r"C:\Program Files (x86)\eSSL\eTimeTrackLite\eTimeTrackLite1.mdb"
SYNC_INTERVAL_MINUTES = 5

# Save state securely in the user's home directory to avoid Windows Permission errors
STATE_FILE = os.path.join(os.path.expanduser("~"), "peoplein_relay_state.json")

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
                pass # Silent heartbeat on success so we don't spam terminal
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat error: {e}")
        
        # Run every 60 seconds
        time.sleep(60)

def test_database():
    try:
        conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={MDB_PATH};"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM Employees")
        emp_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM AttendanceLogs")
        att_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT TOP 1 AttendanceDate FROM AttendanceLogs ORDER BY attendanceLogId DESC")
        latest_date_row = cursor.fetchone()
        latest_date = latest_date_row[0] if latest_date_row else "No records"
        
        print(f"--- DB DIAGNOSTICS ---")
        print(f"Total Employees: {emp_count}")
        print(f"Total Logs: {att_count}")
        print(f"Latest Date in DB: {latest_date}")
        print(f"----------------------\n")
        
        conn.close()
    except Exception as e:
        print(f"DB Diagnostic Error: {e}")

def sync_attendance():
    while True:
        try:
            state = load_state()
            last_id = state["lastAttendanceLogId"]

            conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={MDB_PATH};"
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Remove flaky MS Access date filter, we will filter in Python
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
                ORDER BY a.attendanceLogId ASC
            """

            cursor.execute(query, last_id)
            rows = cursor.fetchall()

            if not rows:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Fully synced! Waiting 5 minutes...")
                conn.close()
            else:
                records_payload = []
                new_max_id = last_id

                for row in rows:
                    log_id = row[0]
                    emp_code = str(row[1]) if row[1] is not None else ""
                    
                    if log_id > new_max_id:
                        new_max_id = log_id

                    # Smart parser that tries all common formats
                    def parse_datetime_smart(val):
                        if not val: return None
                        if hasattr(val, 'strftime'): return val
                        
                        s = str(val).strip()
                        formats = [
                            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
                            "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
                            "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"
                        ]
                        for fmt in formats:
                            try:
                                return datetime.strptime(s, fmt)
                            except ValueError:
                                pass
                        return None

                    dt_att = parse_datetime_smart(row[2])
                    dt_in = parse_datetime_smart(row[3])
                    dt_out = parse_datetime_smart(row[4])
                    
                    # Filter out old records in Python!
                    first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    if dt_att and dt_att < first_of_month:
                        continue # Skip records older than this month
                    
                    att_date = dt_att.strftime("%Y-%m-%d") if dt_att else ""
                    in_time = dt_in.strftime("%Y-%m-%dT%H:%M:%S") + "Z" if dt_in else None
                    out_time = dt_out.strftime("%Y-%m-%dT%H:%M:%S") + "Z" if dt_out else None
                    
                    duration = int(row[5]) if row[5] is not None else 0
                    late_by = int(row[6]) if row[6] is not None else 0
                    early_by = int(row[7]) if row[7] is not None else 0

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

                if len(records_payload) == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fast-forwarding {len(rows)} old records (ID: {last_id} -> {new_max_id})...")
                    state["lastAttendanceLogId"] = new_max_id
                    save_state(state)
                    continue # IMMEDIATELY fetch the next 500 without waiting 5 minutes!
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(records_payload)} records from this month. Syncing to API...")

                    url = f"{API_URL}/api/v1/relay/attendance/sync"
                    headers = {
                        "X-API-Key": API_KEY,
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post(url, json={"records": records_payload}, headers=headers, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] API Sync Success! Log ID updated to {new_max_id}")
                        state["lastAttendanceLogId"] = new_max_id
                        save_state(state)
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] API Sync Failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sync error: {e}")

        # Sleep for the configured interval only if we didn't fast-forward
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping for {SYNC_INTERVAL_MINUTES} minutes...")
        time.sleep(SYNC_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    print("=========================================")
    print(" PeopleIN Relay - Headless Python Script")
    print("=========================================")
    
    test_database()
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Start sync loop in main thread
    sync_attendance()
