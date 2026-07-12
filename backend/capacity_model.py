from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta

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
