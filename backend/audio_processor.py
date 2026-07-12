import librosa
import numpy as np
import base64
import io
import soundfile as sf
import tempfile
import os

def analyze_audio_biomarkers(base64_audio: str) -> dict:
    """
    Decodes base64 audio, loads it via librosa, and extracts 
    basic acoustic biomarkers (pitch/frequency stability, coughing/wheezing signatures).
    """
    try:
        # Strip data URL prefix if present
        if "base64," in base64_audio:
            base64_audio = base64_audio.split("base64,")[1]
            
        audio_data = base64.b64decode(base64_audio)
        
        # Write to a temporary file because librosa relies on soundfile which likes file paths
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
            
        try:
            # Load audio using librosa
            y, sr = librosa.load(temp_audio_path, sr=None)
            
            # Feature 1: Zero Crossing Rate (high variance can indicate coughing/wheezing/irregular breathing)
            zcr = librosa.feature.zero_crossing_rate(y)
            zcr_mean = np.mean(zcr)
            zcr_var = np.var(zcr)
            
            # Feature 2: Spectral Centroid (brightness of sound)
            cent = librosa.feature.spectral_centroid(y=y, sr=sr)
            cent_mean = np.mean(cent)
            
            # Feature 3: Fundamental Frequency (f0) via Yin (pitch tracking)
            f0 = librosa.yin(y, fmin=50, fmax=500)
            f0_valid = f0[f0 > 0]
            pitch_mean = np.mean(f0_valid) if len(f0_valid) > 0 else 0
            pitch_std = np.std(f0_valid) if len(f0_valid) > 0 else 0
            
            # Basic Heuristic logic to extract clinical insights
            insights = []
            if zcr_var > 0.05:
                insights.append("High variance in zero-crossing rate detected (Possible coughing, wheezing, or laboured breathing).")
            if pitch_std > 20:
                insights.append("High pitch instability detected (Possible vocal cord distress or shortness of breath).")
                
            if not insights:
                insights.append("Normal vocal acoustic patterns.")
                
            return {
                "status": "success",
                "insights": insights,
                "metrics": {
                    "zcr_mean": float(zcr_mean),
                    "zcr_variance": float(zcr_var),
                    "spectral_centroid_mean": float(cent_mean),
                    "pitch_mean": float(pitch_mean),
                    "pitch_instability": float(pitch_std)
                }
            }
            
        finally:
            os.remove(temp_audio_path)
            
    except Exception as e:
        print(f"Error processing audio with librosa: {e}")
        return {
            "status": "error",
            "insights": ["Could not process audio segment."],
            "error": str(e)
        }
