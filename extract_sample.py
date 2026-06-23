import pyodbc
import json
from datetime import datetime

MDB_PATH = r"C:\Program Files (x86)\eSSL\eTimeTrackLite\eTimeTrackLite1.mdb"

def dump_table_sample(cursor, table_name, order_col, limit=5):
    print(f"--- Extracting {limit} rows from {table_name} ---")
    try:
        cursor.execute(f"SELECT TOP {limit} * FROM {table_name} ORDER BY {order_col} DESC")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            row_dict = {}
            for idx, col in enumerate(columns):
                val = row[idx]
                if hasattr(val, 'strftime'):
                    val = val.strftime("%Y-%m-%d %H:%M:%S")
                row_dict[col] = str(val)
            results.append(row_dict)
            
        return results
    except Exception as e:
        print(f"Error reading {table_name}: {e}")
        return []

if __name__ == "__main__":
    conn_str = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={MDB_PATH};"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    data = {
        "AttendanceLogs": dump_table_sample(cursor, "AttendanceLogs", "attendanceLogId", 5),
        "DeviceLogs": dump_table_sample(cursor, "DeviceLogs", "DeviceLogId", 5)
    }
    
    with open("sample_data.json", "w") as f:
        json.dump(data, f, indent=4)
        
    print("Extraction complete! Open 'sample_data.json' in your editor to see the raw data formats.")
    conn.close()
