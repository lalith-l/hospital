import sqlite3
import bcrypt
import time
import urllib.parse
from datetime import datetime
import json
import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "aegis.db"

def init_tables(db: sqlite3.Connection):
    db.execute("""
    CREATE TABLE IF NOT EXISTS hospitals (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      nabh_accredited INTEGER DEFAULT 0,
      tier INTEGER DEFAULT 2,
      lat REAL NOT NULL,
      lng REAL NOT NULL,
      address TEXT,
      phone TEXT,
      emergency_24x7 INTEGER DEFAULT 0,
      total_beds INTEGER,
      google_maps_url TEXT,
      practo_url TEXT,
      source TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS hospital_specialties (
      hospital_id TEXT,
      specialty TEXT,
      FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS question_effectiveness (
        id TEXT PRIMARY KEY,
        symptom_context TEXT NOT NULL,
        question_asked TEXT NOT NULL,
        answer_received TEXT,
        entropy_before REAL,
        entropy_after REAL,
        entropy_reduction REAL,
        final_diagnosis TEXT,
        session_id TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      qualification TEXT,
      specialty TEXT NOT NULL,
      hospital_id TEXT,
      lat REAL,
      lng REAL,
      rating REAL,
      experience_years INTEGER,
      consultation_fee INTEGER,
      practo_url TEXT NOT NULL,
      photo_url TEXT,
      nabh_hospital INTEGER DEFAULT 0,
      available_today INTEGER DEFAULT 1,
      FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS hospital_users (
      id TEXT PRIMARY KEY,
      hospital_id TEXT NOT NULL,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'reception',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS geo_overrides (
      id TEXT PRIMARY KEY,
      city TEXT NOT NULL,
      disease TEXT NOT NULL,
      probability_boost REAL NOT NULL,
      reason TEXT,
      source_url TEXT,
      active_from DATETIME,
      active_until DATETIME,
      created_by TEXT DEFAULT 'admin'
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
      id TEXT PRIMARY KEY,
      session_id TEXT,
      predicted_condition TEXT,
      urgency_level INTEGER,
      patient_city TEXT,
      patient_pincode TEXT,
      hospital_id TEXT,
      patient_phone TEXT,
      status TEXT DEFAULT 'pending',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      acknowledged_at DATETIME,
      acknowledged_latency_seconds REAL,
      FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS triage_sessions (
      id TEXT PRIMARY KEY,
      pincode TEXT,
      symptom_vector TEXT,
      predicted_condition TEXT,
      urgency_level INTEGER,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    db.commit()

async def sync_hospitals(db: sqlite3.Connection):
    hospitals_added = 0
    cursor = db.cursor()

    # Attempt 1 — NHA HFR official API
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://facility.abdm.gov.in/api/v1/facility/search",
                params={
                    "state": "Karnataka",
                    "district": "Bengaluru Urban",
                    "facilityType": "Hospital",
                    "pageNo": 1,
                    "pageSize": 100
                }
            )
            if res.status_code == 200:
                data = res.json()
                facilities = data.get("content") or data.get("facilities") or []
                for idx, f in enumerate(facilities):
                    h_id = f"nha_{f.get('facilityId', idx)}"
                    name = f.get("facilityName", "Unknown Hospital")
                    lat = f.get("latitude")
                    lng = f.get("longitude")
                    if not lat or not lng: continue
                    
                    address = f.get("address", "")
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO hospitals (id, name, lat, lng, address, total_beds, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (h_id, name, float(lat), float(lng), address, 100, "NHA_HFR"))
                    if cursor.rowcount > 0:
                        hospitals_added += 1
            else:
                logger.warning(f"NHA API returned status {res.status_code}: {res.text}")
    except Exception as e:
        logger.warning(f"NHA API failed: {e}")

    # Attempt 2 — OSM Overpass as supplement or fallback
    try:
        overpass_query = """
        [out:json][timeout:25];
        (
          node["amenity"="hospital"]["name"]["addr:city"~"Bangalore|Bengaluru"];
          way["amenity"="hospital"]["name"]["addr:city"~"Bangalore|Bengaluru"];
        );
        out center;
        """
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": overpass_query}
            )
            if res.status_code == 200:
                elements = res.json().get("elements", [])
                for el in elements:
                    name = el.get("tags", {}).get("name")
                    if not name:
                        continue
                    lat = el.get("lat") or el.get("center", {}).get("lat")
                    lng = el.get("lon") or el.get("center", {}).get("lon")
                    if not lat or not lng: continue
                    
                    # fuzzy duplicate check
                    existing = cursor.execute(
                        "SELECT id FROM hospitals WHERE name LIKE ?",
                        (f"%{name[:10]}%",)
                    ).fetchone()
                    if not existing:
                        h_id = f"osm_{el.get('id')}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO hospitals (id, name, lat, lng, total_beds, source)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (h_id, name, float(lat), float(lng), 50, "OSM"))
                        if cursor.rowcount > 0:
                            hospitals_added += 1
            else:
                logger.warning(f"OSM API returned status {res.status_code}")
    except Exception as e:
        logger.warning(f"OSM API failed: {e}")

    if hospitals_added == 0:
        logger.critical("CRITICAL: Both NHA and OSM APIs returned 0 results or failed.")
    else:
        logger.info(f"Hospital sync complete: {hospitals_added} records added")

    db.commit()
    return hospitals_added

def seed_admin_user(db: sqlite3.Connection):
    cursor = db.cursor()
    # Seed Admin User for the first hospital found
    cursor.execute("SELECT id FROM hospitals LIMIT 1")
    row = cursor.fetchone()
    
    if not row:
        # If both APIs failed, create a fallback hospital so the user has a place to attach
        logger.info("No hospitals found from APIs. Creating a fallback hospital 'Manipal Hospital (Fallback)'.")
        fallback_h_id = "h_fallback_1"
        db.execute("""
            INSERT INTO hospitals (id, name, lat, lng, address)
            VALUES (?, ?, ?, ?, ?)
        """, (fallback_h_id, "Manipal Hospital (Fallback)", 12.9716, 77.5946, "Bangalore"))
        db.commit()
        first_h_id = fallback_h_id
    else:
        first_h_id = row[0]

    # Check if user exists
    existing = db.execute("SELECT id FROM hospital_users WHERE username = ?", ("manipal_reception",)).fetchone()
    if not existing:
        logger.info("Seeding default hospital admin user...")
        password_hash = bcrypt.hashpw(b"aegis2024", bcrypt.gensalt()).decode()
        db.execute("""
            INSERT INTO hospital_users (id, hospital_id, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("u1", first_h_id, "manipal_reception", password_hash, "reception"))
        db.commit()

    existing_doc = db.execute("SELECT id FROM hospital_users WHERE username = ?", ("doctor",)).fetchone()
    if not existing_doc:
        logger.info("Seeding default doctor user...")
        password_hash = bcrypt.hashpw(b"doctor123", bcrypt.gensalt()).decode()
        db.execute("""
            INSERT INTO hospital_users (id, hospital_id, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("u2", first_h_id, "doctor", password_hash, "doctor"))
        db.commit()

def seed_doctors(db: sqlite3.Connection):
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] > 0:
        return
        
    print("Seeding manual doctors list...")
    
    # Needs at least one hospital
    cursor.execute("SELECT id FROM hospitals LIMIT 1")
    row = cursor.fetchone()
    if not row:
        return
    h_id = row[0]
    
    REAL_DOCTORS = [
        {
            "id": "d001",
            "name": "Dr. Vivek Murthy",
            "qualification": "MBBS, MD",
            "specialty": "general_physician",
            "hospital_id": h_id,
            "lat": 13.0358, "lng": 77.5970,
            "rating": 4.9,
            "experience_years": 8,
            "consultation_fee": 700,
            "practo_url": "https://www.practo.com/bangalore/doctor/suresh-g-general-physician",
            "nabh_hospital": 1
        },
        {
            "id": "d002",
            "name": "Dr. Anil Kumar",
            "qualification": "MBBS, MS - Orthopaedics",
            "specialty": "orthopedist",
            "hospital_id": h_id,
            "lat": 13.0350, "lng": 77.5965,
            "rating": 4.6,
            "experience_years": 15,
            "consultation_fee": 850,
            "practo_url": "https://www.practo.com/bangalore/doctors",
            "nabh_hospital": 1
        }
    ]
    
    for d in REAL_DOCTORS:
        cursor.execute("""
            INSERT INTO doctors (id, name, qualification, specialty, hospital_id, lat, lng, rating, experience_years, consultation_fee, practo_url, nabh_hospital)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (d["id"], d["name"], d["qualification"], d["specialty"], d["hospital_id"], d["lat"], d["lng"], d["rating"], d["experience_years"], d["consultation_fee"], d["practo_url"], d["nabh_hospital"]))
        
        # Also seed hospital_specialties
        cursor.execute("""
            INSERT INTO hospital_specialties (hospital_id, specialty)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM hospital_specialties WHERE hospital_id = ? AND specialty = ?
            )
        """, (h_id, d["specialty"], h_id, d["specialty"]))
        
    db.commit()

async def run_seeding():
    with sqlite3.connect(DB_PATH) as db:
        init_tables(db)
        # Check if we need to seed
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM hospitals")
        if cursor.fetchone()[0] == 0:
            await sync_hospitals(db)
        else:
            logger.info("Hospitals already seeded.")
        seed_admin_user(db)
        seed_doctors(db)

if __name__ == "__main__":
    asyncio.run(run_seeding())
