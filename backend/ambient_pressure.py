try:
    import diffprivlib as dp
    HAS_DP = True
except ImportError:
    HAS_DP = False

import numpy as np
from datetime import datetime, timedelta

# Hardcoded mapping of Bangalore pincodes to approximate coords for the heatmap
PINCODE_COORDS = {
    "560001": {"lat": 12.9796, "lon": 77.5906}, # MG Road / Shivaji Nagar
    "560034": {"lat": 12.9344, "lon": 77.6225}, # Koramangala
    "560038": {"lat": 12.9784, "lon": 77.6408}, # Indiranagar
    "560011": {"lat": 12.9299, "lon": 77.5815}, # Jayanagar
    "560076": {"lat": 12.8941, "lon": 77.5978}, # Bannerghatta Road
    "560066": {"lat": 12.9818, "lon": 77.7281}, # Whitefield
    "560103": {"lat": 12.9328, "lon": 77.6841}, # Bellandur
    "560022": {"lat": 13.0238, "lon": 77.5457}, # Yeshwanthpur
    "560099": {"lat": 12.8123, "lon": 77.6836}, # Bommasandra
    "560060": {"lat": 12.9022, "lon": 77.4988}, # Kengeri
    "560004": {"lat": 12.9554, "lon": 77.5750}, # V.V. Puram
    "560024": {"lat": 13.0426, "lon": 77.5946}, # Hebbal
    "560054": {"lat": 13.0306, "lon": 77.5647}, # Mathikere
}

def compute_ambient_pressure(pincode: str, db_conn):
    cutoff = datetime.now() - timedelta(hours=48)
    
    # We group by condition to get counts
    cursor = db_conn.cursor()
    sessions = cursor.execute("""
        SELECT predicted_condition, COUNT(*) as count
        FROM triage_sessions 
        WHERE pincode = ? AND timestamp > ?
        GROUP BY predicted_condition
    """, (pincode, cutoff)).fetchall()
    
    if not sessions:
        return {"status": "insufficient_data", "sessions_count": 0, "pressure": {}}
    
    total = sum(s["count"] for s in sessions)
    
    # Minimum threshold — suppress if too few sessions
    if total < 5:
        return {"status": "insufficient_data", "sessions_count": total, "pressure": {}}
    
    # Apply Laplace differential privacy noise
    # epsilon=1.0 is standard privacy budget, sensitivity=1 because we're counting
    pressure = {}
    for session in sessions:
        condition = session["predicted_condition"]
        count = session["count"]
        
        if HAS_DP:
            mech = dp.mechanisms.Laplace(epsilon=1.0, sensitivity=1.0)
            noisy_count = max(0, mech.randomise(float(count)))
        else:
            noisy_count = max(0, float(count) + np.random.laplace(0, 1.0))
            
        pressure[condition] = round(noisy_count / total, 3)
    
    # Sort by pressure descending
    pressure = dict(sorted(pressure.items(), key=lambda x: x[1], reverse=True))
    
    if not pressure:
        return {"status": "insufficient_data", "sessions_count": total, "pressure": {}}
        
    return {
        "status": "active",
        "pincode": pincode,
        "window_hours": 48,
        "sessions_count": total,
        "pressure": pressure,
        "lead_condition": list(pressure.keys())[0],
        "lead_probability": list(pressure.values())[0]
    }

def get_all_active_pressures(db_conn):
    """
    Returns heatmap data points for all pincodes with active signals.
    Format: [{"lat": 12.9, "lon": 77.5, "intensity": 0.8, "condition": "Dengue", "pincode": "560001"}]
    """
    cursor = db_conn.cursor()
    # Get distinct pincodes from last 48 hours
    cutoff = datetime.now() - timedelta(hours=48)
    rows = cursor.execute("SELECT DISTINCT pincode FROM triage_sessions WHERE timestamp > ?", (cutoff,)).fetchall()
    
    heatmap_data = []
    for row in rows:
        pincode = row["pincode"]
        coords = PINCODE_COORDS.get(pincode)
        if not coords:
            continue
            
        ambient = compute_ambient_pressure(pincode, db_conn)
        if ambient["status"] == "active":
            heatmap_data.append({
                "lat": coords["lat"],
                "lon": coords["lon"],
                "intensity": ambient["lead_probability"],
                "condition": ambient["lead_condition"],
                "pincode": pincode,
                "sessions_count": ambient["sessions_count"]
            })
            
    return heatmap_data
