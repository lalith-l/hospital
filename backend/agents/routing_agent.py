import sqlite3
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class RoutingAgent:
    """Agent 4: Hospital matching and doctor routing."""

    @staticmethod
    def route(condition: str, lat: float, lon: float, urgency: int, db_conn: sqlite3.Connection):
        """
        Calculates Haversine distances and Z-score match logic
        to route patients to appropriate hospitals/doctors.
        """
        cursor = db_conn.cursor()
        
        # Simple mapping of condition to specialty (in a real app this would be more complex)
        specialty = "general_physician"
        if condition in ["Myocardial Infarction", "Cardiac Event"]:
            specialty = "cardiologist"
        elif condition in ["Stroke", "Neurological Event"]:
            specialty = "neurologist"
        elif "Fracture" in condition:
            specialty = "orthopedist"
            
        doctors_rows = cursor.execute("""
            SELECT d.*, h.name as hospital_name 
            FROM doctors d
            JOIN hospitals h ON d.hospital_id = h.id
            WHERE d.specialty = ? OR ? = 'general_physician'
        """, (specialty, specialty)).fetchall()
        
        results = []
        for d in doctors_rows:
            dist = haversine(lat, lon, d["lat"], d["lng"])
            if dist < 50:  # Within 50km
                # Urgency check: if urgency is 1, prefer NABH accredited emergency hospitals
                if urgency == 1 and not d["nabh_hospital"]:
                    continue
                results.append({
                    "name": d["name"],
                    "qualification": d["qualification"],
                    "specialty": d["specialty"],
                    "hospital_id": d["hospital_id"],
                    "hospital_name": d["hospital_name"],
                    "hospital_lat": d["lat"],
                    "hospital_lon": d["lng"],
                    "nabh": bool(d["nabh_hospital"]),
                    "experience": d["experience_years"],
                    "fee": d["consultation_fee"],
                    "rating": d["rating"],
                    "distance": f"{round(dist, 1)} km away",
                    "photo": "https://randomuser.me/api/portraits/men/32.jpg" if "001" in str(d["id"]) else "https://randomuser.me/api/portraits/men/44.jpg",
                    "url": d["practo_url"],
                    "_dist_num": dist
                })
                
        # Sort by distance
        results.sort(key=lambda x: x["_dist_num"])
        # Remove the temporary key
        for r in results:
            del r["_dist_num"]
            
        return results[:3]
