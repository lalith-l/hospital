import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'aegis.db')

def init_db():
    print(f"Initializing database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        predicted_condition TEXT,
        urgency_level INTEGER,
        patient_city TEXT,
        patient_pincode TEXT,
        image_evidence_url TEXT,
        pdf_url TEXT,
        hospital_id TEXT,
        patient_phone TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP,
        acknowledged_at TIMESTAMP,
        acknowledged_latency_seconds REAL,
        expected_latency_seconds REAL,
        anomaly_score REAL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS triage_sessions (
        id TEXT PRIMARY KEY,
        pincode TEXT NOT NULL,
        symptom_vector TEXT NOT NULL,
        predicted_condition TEXT NOT NULL,
        urgency_level INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == '__main__':
    init_db()
