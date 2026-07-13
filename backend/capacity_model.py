from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta
import json
import os
import time
def get_hospital_baseline(hospital_id, db_conn):
    """
    Get historical acknowledgement latency for this hospital
    broken down by day_of_week and hour_of_day
    Using last 30 days of data
    """
    cutoff = datetime.now() - timedelta(days=30)
    
    # We use sqlite strftime. 
    # %w is 0-6 (Sunday-Saturday)
    # %H is 00-24
    cursor = db_conn.cursor()
    history = cursor.execute("""
        SELECT 
            strftime('%w', created_at) as dow,
            strftime('%H', created_at) as hour,
            acknowledged_latency_seconds
        FROM alerts
        WHERE hospital_id = ?
        AND acknowledged_latency_seconds IS NOT NULL
        AND created_at > ?
    """, (hospital_id, cutoff)).fetchall()
    
    if len(history) < 10:
        # Not enough data — return None (use fallback)
        return None
    
    # Build baseline: expected latency by dow + hour
    baseline = defaultdict(list)
    for row in history:
        key = f"{row['dow']}_{row['hour']}"
        baseline[key].append(row['acknowledged_latency_seconds'])
    
    # Compute mean and std per slot
    stats = {}
    for key, latencies in baseline.items():
        stats[key] = {
            "mean": np.mean(latencies),
            "std": max(np.std(latencies), 60)  # min 60s std
        }
    
    return stats


def compute_hospital_load(hospital_id, db_conn):
    """
    Returns real-time load assessment for a hospital
    """
    now = datetime.now()
    
    # Get current unacknowledged alerts
    cursor = db_conn.cursor()
    pending = cursor.execute("""
        SELECT id, created_at, urgency_level
        FROM alerts
        WHERE hospital_id = ? AND status = 'pending'
    """, (hospital_id,)).fetchall()
    
    pending_count = len(pending)
    
    # Compute current wait times for pending alerts
    current_waits = []
    for row in pending:
        # Parse sqlite timestamp: 'YYYY-MM-DD HH:MM:SS.mmmmmm'
        created_at_str = row['created_at']
        try:
            if '.' in created_at_str:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S.%f')
            else:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            # Fallback if unparseable
            created_at = now
            
        wait = (now - created_at).total_seconds()
        current_waits.append(wait)
    
    avg_current_wait = np.mean(current_waits) if current_waits else 0
    
    # Get baseline for current time slot
    baseline = get_hospital_baseline(hospital_id, db_conn)
    
    if baseline is None:
        # Cold start — use simple pending count heuristic
        if pending_count == 0:
            return {"load": "Low", "score": 0.1, "method": "heuristic", "pending": 0}
        elif pending_count <= 2:
            return {"load": "Medium", "score": 0.5, "method": "heuristic", "pending": pending_count}
        else:
            return {"load": "High", "score": 0.9, "method": "heuristic", "pending": pending_count}
    
    # Anomaly detection using z-score
    # In Python weekday() is 0=Monday, 6=Sunday
    # SQLite strftime('%w') is 0=Sunday, 6=Saturday
    # Convert python weekday to SQLite format: (now.weekday() + 1) % 7
    sqlite_dow = str((now.weekday() + 1) % 7)
    hour = str(now.hour).zfill(2)
    key = f"{sqlite_dow}_{hour}"
    
    if key in baseline:
        expected_mean = baseline[key]["mean"]
        expected_std = baseline[key]["std"]
        
        # Z-score of current wait vs historical baseline
        z_score = (avg_current_wait - expected_mean) / expected_std
        
        # Normalize to 0-1 load score
        load_score = min(1.0, max(0.0, (z_score + 2) / 4))
        
        if z_score < 0.5:
            load_label = "Low"
        elif z_score < 1.5:
            load_label = "Medium"  
        else:
            load_label = "High"
            
        return {
            "load": load_label,
            "score": round(load_score, 2),
            "z_score": round(z_score, 2),
            "avg_wait_seconds": round(avg_current_wait),
            "expected_wait_seconds": round(expected_mean),
            "pending_alerts": pending_count,
            "method": "baseline_comparison"
        }
    else:
        # No baseline for this time slot yet
        return {"load": "Unknown", "score": 0.5, "method": "no_baseline", "pending": pending_count}


# --- NEW RESOURCE BOTTLENECK MAPPING LOGIC ---

class SessionStore:
    """
    Abstracted Session Store, defaulting to in-memory dict for local dev.
    Can be easily swapped with Redis for production multi-worker environments.
    """
    def __init__(self):
        self._store = {}
    
    def update_session(self, session_id, ddx_probs, is_complete=False):
        if is_complete:
            self.remove_session(session_id)
        else:
            self._store[session_id] = {
                "ddx_probs": ddx_probs,
                "last_updated": time.time()
            }
            
    def remove_session(self, session_id):
        self._store.pop(session_id, None)
        
    def get_all_active(self):
        # Garbage Collection (15 min TTL)
        now = time.time()
        stale_keys = [k for k, v in self._store.items() if (now - v["last_updated"]) > 900]
        for k in stale_keys:
            self.remove_session(k)
            
        return list(self._store.values())

# Global singleton for local dev
active_session_store = SessionStore()

def load_pathways():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pathways_file = os.path.join(base_dir, "pathways.json")
    if os.path.exists(pathways_file):
        with open(pathways_file, "r") as f:
            return json.load(f)
    return {}

PATHWAYS = load_pathways()

def calculate_bottlenecks():
    """
    Computes expected resource demand globally using live differential probabilities.
    Includes Probability Clamping per-patient.
    """
    sessions = active_session_store.get_all_active()
    
    # Track raw demand
    resource_demand = defaultdict(float)
    
    for session in sessions:
        ddx_probs = session.get("ddx_probs", [])
        
        # Track this patient's demand on each resource to clamp it
        patient_resource_demand = defaultdict(float)
        
        for p in ddx_probs:
            condition = p.get("condition")
            probability = p.get("probability", 0.0)
            
            if condition in PATHWAYS:
                for mapping in PATHWAYS[condition]:
                    res = mapping["resource"]
                    weight = mapping["weight"]
                    patient_resource_demand[res] += (probability * weight)
        
        # Add clamped demand to global tally (Probability Clamping)
        for res, total_demand in patient_resource_demand.items():
            resource_demand[res] += min(total_demand, 1.0)
            
    # Normalize global demand (e.g., max physical capacity could be defined, 
    # here we normalize assuming a scaling factor or just returning raw demand mapped 0-1)
    # A simple normalization for demonstration: map 0-5 demand to 0.0-1.0 intensity
    # (Assuming a small clinic where 5 concurrent patients needing a resource is a bottleneck)
    
    normalized_results = []
    # For demo purposes, we set MAX_CAPACITY to 1.0 so a single triage session 
    # immediately triggers the visual threshold (>0.4 intensity)
    MAX_CAPACITY = 1.0 
    
    for res, raw_val in resource_demand.items():
        intensity = min(raw_val / MAX_CAPACITY, 1.0)
        normalized_results.append({
            "resource": res,
            "intensity": intensity
        })
        
    return normalized_results
