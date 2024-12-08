from flask import Flask, g, request, jsonify
import sqlite3
from datetime import datetime
import signal
import sys

app = Flask(__name__)

DATABASE = "parking_lot.db"

# Helper to get the database connection
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# Teardown to close the database connection
@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# Parking Lot class
class ParkingLot:
    def __init__(self):
        self.conn = get_db()

    def park_vehicle(self, vehicle_number):
        cursor = self.conn.cursor()
        cursor.execute("SELECT slot_id FROM parking_slots WHERE vehicle_number IS NULL LIMIT 1")
        slot = cursor.fetchone()
        if slot:
            slot_id = slot[0]
            entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "UPDATE parking_slots SET vehicle_number = ?, entry_time = ? WHERE slot_id = ?",
                (vehicle_number, entry_time, slot_id)
            )
            self.conn.commit()
            return {"slot_id": slot_id, "message": "Vehicle parked successfully"}
        else:
            return {"message": "No available slots"}

    def exit_vehicle(self, vehicle_number):
        cursor = self.conn.cursor()
        cursor.execute("SELECT slot_id FROM parking_slots WHERE vehicle_number = ? LIMIT 1", (vehicle_number,))
        slot = cursor.fetchone()
        if slot:
            slot_id = slot[0]
            cursor.execute("UPDATE parking_slots SET vehicle_number = NULL, entry_time = NULL WHERE slot_id = ?", (slot_id,))
            self.conn.commit()
            return {"message": f"Vehicle {vehicle_number} exited, slot {slot_id} is now available."}
        else:
            return {"message": "Vehicle not found in the parking lot."}

# Instantiate the ParkingLot class
@app.route('/park', methods=['POST'])
def park_vehicle():
    parking_lot = ParkingLot()
    vehicle_number = request.json.get("vehicle_number")
    response = parking_lot.park_vehicle(vehicle_number)
    return jsonify(response)

@app.route('/exit', methods=['POST'])
def exit_vehicle():
    parking_lot = ParkingLot()
    vehicle_number = request.json.get("vehicle_number")
    response = parking_lot.exit_vehicle(vehicle_number)
    return jsonify(response)

def initialize_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT,
            entry_time TEXT
        )
    ''')
    # Insert sample slots if the table is empty
    cursor.execute('SELECT COUNT(*) FROM parking_slots')
    if cursor.fetchone()[0] == 0:
        # Assuming 10 parking slots for simplicity
        cursor.executemany('INSERT INTO parking_slots (vehicle_number, entry_time) VALUES (NULL, NULL)', [()] * 10)
    conn.commit()
    conn.close()

def handle_exit(signal, frame):
    print("Gracefully shutting down the server.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

if __name__ == '__main__':
    initialize_db()

    # Add workaround for "Bad file descriptor" error
    import os
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("Starting server...")

    app.run(debug=True, use_reloader=False)  # Disable reloader







