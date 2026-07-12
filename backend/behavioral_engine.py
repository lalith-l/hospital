import numpy as np

def normalize(value, min_val, max_val):
    if value <= min_val: return 0.0
    if value >= max_val: return 1.0
    return (value - min_val) / (max_val - min_val)

def compute_coherence(behavioral_history, verbal_severity):
    """
    Computes cross-modal behavioral coherence from raw metrics.
    """
    if not behavioral_history or len(behavioral_history) < 2:
        return None
        
    latencies = [turn.get("latency_ms", 0) for turn in behavioral_history]
    rms_energies = [turn.get("vocal", {}).get("rms_energy", 0) for turn in behavioral_history]
    speech_rates = [turn.get("vocal", {}).get("speech_rate", 0) for turn in behavioral_history]
    
    x = np.arange(len(behavioral_history))
    
    # 1. Latency Slope
    # Polyfit returns [slope, intercept]. If latencies are constant, slope is 0.
    latency_slope = np.polyfit(x, latencies, 1)[0]
    
    # 2. Vocal Slopes (only use turns where audio was actually recorded)
    vocal_indices = [i for i, v in enumerate(rms_energies) if v > 0.001]
    if len(vocal_indices) > 1:
        valid_x = np.array(vocal_indices)
        valid_rms = np.array([rms_energies[i] for i in vocal_indices])
        valid_sr = np.array([speech_rates[i] for i in vocal_indices])
        
        # Check for sufficient variance to avoid RankWarning
        if np.std(valid_rms) > 0:
            energy_slope = np.polyfit(valid_x, valid_rms, 1)[0]
        else:
            energy_slope = 0
            
        if np.std(valid_sr) > 0:
            sr_slope = np.polyfit(valid_x, valid_sr, 1)[0]
        else:
            sr_slope = 0
    else:
        energy_slope = 0
        sr_slope = 0
        
    # 3. Keystroke Aggregates
    all_intervals = []
    total_keys = 0
    total_backspaces = 0
    
    for turn in behavioral_history:
        ks = turn.get("keystrokes", {})
        all_intervals.extend(ks.get("inter_key_intervals", []))
        total_keys += ks.get("total_keys", 0)
        total_backspaces += ks.get("backspaces", 0)
        
    avg_inter_key = np.mean(all_intervals) if all_intervals else 180
    backspace_ratio = (total_backspaces / total_keys) if total_keys > 0 else 0
    
    # Normalize severities (0.0 = healthy, 1.0 = highly symptomatic)
    
    # Vocal: negative energy slope (fatigue)
    vocal_sev = normalize(-energy_slope, 0.0, 0.05)
    
    # Keystroke: higher inter-key interval (cognitive slowing), high backspaces (erratic)
    ks_sev_1 = normalize(avg_inter_key, 200, 600)
    ks_sev_2 = normalize(backspace_ratio, 0.05, 0.30)
    ks_sev = (ks_sev_1 + ks_sev_2) / 2
    
    # Latency: positive latency slope (slowing down over time)
    latency_sev = normalize(latency_slope, 100, 2000)
    
    # Average behavioral severity
    behavioral_severity = np.mean([vocal_sev, ks_sev, latency_sev])
    
    # Formatting Trend Indicators for UI
    if energy_slope < -0.01:
        vocal_trend = "↓ declining"
    elif energy_slope > 0.01:
        vocal_trend = "↑ increasing"
    else:
        vocal_trend = "→ stable"
        
    if avg_inter_key > 350 or backspace_ratio > 0.2:
        ks_trend = "↓ slowing"
    elif avg_inter_key < 150:
        ks_trend = "↑ fast"
    else:
        ks_trend = "→ stable"
        
    if latency_slope > 300:
        lat_trend = "↑ increasing"
    elif latency_slope < -300:
        lat_trend = "↓ decreasing"
    else:
        lat_trend = "→ stable"
        
    # Coherence Calculation
    coherence_gap = abs(verbal_severity - behavioral_severity)
    
    if coherence_gap < 0.2:
        label = "COHERENT — verbal matches behavioral"
    elif verbal_severity > behavioral_severity + 0.2:
        label = "OVERSTATEMENT — behavioral signals lighter than claimed"  
    else:
        label = "UNDERSTATEMENT — behavioral signals heavier than claimed"
        
    coherence_score = max(0.0, 1.0 - coherence_gap)
        
    return {
        "coherence_score": coherence_score,
        "label": label,
        "vocal_severity": float(vocal_sev),
        "keystroke_severity": float(ks_sev),
        "latency_severity": float(latency_sev),
        "verbal_severity": float(verbal_severity),
        "vocal_trend": vocal_trend,
        "keystroke_trend": ks_trend,
        "latency_trend": lat_trend,
        "behavioral_severity": float(behavioral_severity)
    }
