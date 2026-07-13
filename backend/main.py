from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
import asyncio
import capacity_model
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import llm
import os
import pdf_generator
import audio_processor
import ddx_retrieval
import behavioral_engine
import datetime
import uuid
import watchdog
import sqlite3
import bcrypt
import jwt
import seed_db
from agents.intake_agent import IntakeAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.guideline_agent import GuidelineAgent
from agents.routing_agent import RoutingAgent
import agents.clinical_rules as clinical_rules
import agents.discriminating_pairs as discriminating_pairs
import math
import uuid
import datetime
from fastapi import Header, Depends
import qr_helper
import twilio_helper
import ambient_pressure

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "CRITICAL: JWT_SECRET environment variable not set. "
        "Generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    )

DB_PATH = os.path.join(os.path.dirname(__file__), 'aegis.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

app = FastAPI(title="Predictive Patient Pathfinder API")


# --- Resource Bottleneck WebSocket ---
active_ws_connections = []
resource_monitor_task = None

async def broadcast_resource_bottlenecks():
    while True:
        try:
            # Check for stale tokens in active connections
            now = datetime.datetime.utcnow()
            valid_connections = []
            for ws, exp_time in active_ws_connections:
                if exp_time < now:
                    await ws.close(code=1008, reason="Token Expired")
                else:
                    valid_connections.append((ws, exp_time))
            
            active_ws_connections.clear()
            active_ws_connections.extend(valid_connections)
            
            if active_ws_connections:
                data = capacity_model.calculate_bottlenecks()
                payload = {
                    "type": "HEATMAP_UPDATE",
                    "data": data
                }
                for ws, _ in active_ws_connections:
                    try:
                        await ws.send_json(payload)
                    except:
                        pass
        except Exception as e:
            print(f"Error in resource monitor loop: {e}")
            
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    global resource_monitor_task
    resource_monitor_task = asyncio.create_task(broadcast_resource_bottlenecks())
    await seed_db.run_seeding()

@app.on_event("shutdown")
async def shutdown_event():
    global resource_monitor_task
    if resource_monitor_task:
        resource_monitor_task.cancel()

@app.websocket("/ws/resource-map")
async def websocket_resource_map(websocket: WebSocket, token: str = None):
    await websocket.accept()
    if not token:
        await websocket.close(code=1008, reason="Missing Token")
        return
        
    try:
        payload = jwt.decode(token, os.environ.get("JWT_SECRET", "super-secret"), algorithms=["HS256"])
        if payload.get("role") != "doctor":
            await websocket.close(code=1008, reason="Unauthorized Role")
            return
            
        exp_timestamp = payload.get("exp")
        exp_time = datetime.datetime.utcfromtimestamp(exp_timestamp) if exp_timestamp else datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        
        active_ws_connections.append((websocket, exp_time))
        
        # Send initial data immediately
        initial_data = capacity_model.calculate_bottlenecks()
        try:
            await websocket.send_json({"type": "HEATMAP_UPDATE", "data": initial_data})
        except Exception:
            return
        
        
        try:
            while True:
                await websocket.receive_text() # Just keep connection open
        except WebSocketDisconnect:
            active_ws_connections.remove((websocket, exp_time))
            
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token Expired")
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid Token")


# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    # Replace the wildcard with your explicit frontend URL
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5175", "http://127.0.0.1:5175"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)

def verify_token(authorization: str = Header(...)):
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid token format")
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(body: LoginRequest):
    db = get_db()
    user = db.execute("SELECT * FROM hospital_users WHERE username = ?", (body.username,)).fetchone()
    db.close()
    
    if not user:
        raise HTTPException(401, "Invalid credentials")
        
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Invalid credentials")
        
    token = jwt.encode({
        "user_id": user["id"],
        "hospital_id": user["hospital_id"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, os.environ.get("JWT_SECRET", "super-secret"), algorithm="HS256")
    
    return {"token": token, "hospital_id": user["hospital_id"], "role": user["role"]}

class Message(BaseModel):
    role: str
    content: str

class IntakeChatRequest(BaseModel):
    messages: List[Message]
    image: Optional[str] = None
    audio: Optional[str] = None
    city: Optional[str] = None
    month: Optional[str] = None
    session_id: Optional[str] = None

class IntakeExtractRequest(BaseModel):
    messages: List[Message]

class ComputeTriageRequest(BaseModel):
    extracted_symptoms: List[str]
    verbal_severity: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    month: Optional[str] = None
    pincode: Optional[str] = None
    behavioral_history: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Predictive Patient Pathfinder API is running"}

import json

@app.post("/api/intake/chat")
def intake_chat(request: IntakeChatRequest):
    if not os.environ.get("GROQ_API_KEY"):
         raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on the server.")

    llm_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Process image if provided
    if request.image:
        vision_findings = llm.analyze_image(request.image)
        visual_context = f"[SYSTEM: Patient uploaded an image. Visual Severity Level: {vision_findings.get('visual_severity')}. Key Findings: {vision_findings.get('key_findings')}."
        llm_messages.insert(0, {"role": "system", "content": visual_context})
        
    # Process audio if provided
    if request.audio:
        audio_findings = audio_processor.analyze_audio_biomarkers(request.audio)
        if audio_findings.get("status") == "success":
            insights = " ".join(audio_findings.get("insights", []))
            audio_context = f"[SYSTEM: Patient recorded audio. Real acoustic biomarker analysis: {insights}]"
            llm_messages.insert(0, {"role": "system", "content": audio_context})
            
    dynamic_context = f"Geographical Prior: {request.city}, {request.month}."
    
    # === CLINICAL ACCURACY FIXES ===
    source = "llm_generated"
    final_question = None
    entropy = 0.0
    
    # 1. Extract current symptoms statelessly to get context
    extracted_data = IntakeAgent.extract_symptoms(llm_messages)
    current_symptoms = extracted_data.get("symptoms", [])
    
    ddx_probs = []
    if current_symptoms:
        # 2. Get current differentials to compute entropy
        ddx_result = DiagnosisAgent.compute_differential(current_symptoms)
        ddx_probs = ddx_result.get("probabilities", [])
        
        # 3. Update active session store for spatial heatmap
        if request.session_id:
            capacity_model.active_session_store.update_session(request.session_id, ddx_probs)
    else:
        # Clear session if no symptoms are detected yet
        if request.session_id:
            capacity_model.active_session_store.remove_session(request.session_id)
        
        # Calculate entropy
        for p in ddx_probs:
            prob = p.get("probability", 0)
            if prob > 0:
                entropy -= prob * math.log2(prob)
                
        if len(ddx_probs) >= 2:
            top1 = ddx_probs[0]
            top2 = ddx_probs[1]
            
            # IMPROVEMENT 3: Discriminating Question Pairs
            if (top1["probability"] - top2["probability"]) < 0.15:
                disc_q = discriminating_pairs.get_discriminating_question([top1["condition"], top2["condition"]])
                if disc_q:
                    final_question = disc_q
                    source = "discriminating_pair"
                    
        # IMPROVEMENT 1: Historical Question Effectiveness
        if not final_question and request.session_id:
            conn = get_db()
            cursor = conn.cursor()
            context_key = json.dumps(sorted(current_symptoms))
            historical = cursor.execute("""
                SELECT question_asked, AVG(entropy_reduction) as avg_reduction,
                       COUNT(*) as times_asked
                FROM question_effectiveness
                WHERE symptom_context LIKE ?
                AND entropy_reduction > 0.1
                GROUP BY question_asked
                ORDER BY avg_reduction DESC
                LIMIT 5
            """, (f"%{context_key[:50]}%",)).fetchall()
            conn.close()
            
            if historical and historical[0]["times_asked"] >= 3:
                final_question = historical[0]["question_asked"]
                source = "learned_from_history"

    if not final_question:
        # Call the INTAKE AGENT (LLM)
        result = IntakeAgent.chat(llm_messages, dynamic_context)
        if result.get("status") == "error":
            return result
            
        final_question_raw = result.get("message", "")
        if isinstance(final_question_raw, dict):
            final_question = final_question_raw.get("text", str(final_question_raw))
        else:
            final_question = str(final_question_raw)
        
        # IMPROVEMENT 2: Clinical Question Validator
        if current_symptoms and result.get("status") == "question":
            top_cond = ddx_probs[0]["condition"] if 'ddx_probs' in locals() and ddx_probs else None
            if top_cond:
                past_questions = " ".join([m.content for m in request.messages if m.role == 'assistant'])
                validation = clinical_rules.validate_question(final_question, top_cond, past_questions)
                if not validation["approved"] and validation.get("override"):
                    final_question = validation["override"]
                    source = "clinical_validator_override"
                elif not validation["approved"]:
                    # Just ask generic if completely banned
                    final_question = "Could you tell me a little more about your symptoms?"
                    source = "clinical_validator_override"

        result["message"] = final_question
        result["question_source"] = source
    else:
        result = {
            "status": "question",
            "message": final_question,
            "simulated_acoustic_signals": [],
            "question_source": source
        }

    # Log the question effectiveness tracking if it's a question
    if result.get("status") == "question" and request.session_id:
        conn = get_db()
        cursor = conn.cursor()
        q_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO question_effectiveness 
            (id, symptom_context, question_asked, entropy_before, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (q_id, json.dumps(current_symptoms), final_question, entropy, request.session_id))
        conn.commit()
        conn.close()
        
    return result

@app.post("/api/intake/extract")
def intake_extract(request: IntakeExtractRequest):
    llm_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    return IntakeAgent.extract_symptoms(llm_messages)

@app.post("/api/triage/compute")
def compute_triage(request: ComputeTriageRequest):
    extracted_symptoms = request.extracted_symptoms
    verbal_severity = request.verbal_severity
    
    # Health Literacy Corrector
    literacy_tier = "High"
    if request.pincode and request.pincode.startswith("5"):
        literacy_tier = "Low"
        
    # Merge Geo Priors with Ambient Signal
    geo_priors_raw = {}
    elevated_risk = "General Risk"
    try:
        with open("geo_priors.json", "r") as f:
            priors = json.load(f)
            if request.city and request.month:
                base = priors.get(request.city, {}).get(request.month, {})
                elevated_risk = base.get("label", "General Risk")
                
                for p in base.get("priors", []):
                    geo_priors_raw[p["disease"]] = p["probability"]
                
                # Fetch live overrides from DB
                conn = get_db()
                overrides = conn.execute("""
                    SELECT disease, probability_boost FROM geo_overrides
                    WHERE city = ? AND active_from <= CURRENT_TIMESTAMP AND active_until >= CURRENT_TIMESTAMP
                """, (request.city,)).fetchall()
                conn.close()
                
                for override in overrides:
                    disease = override["disease"]
                    boost = override["probability_boost"]
                    if disease in geo_priors_raw:
                        geo_priors_raw[disease] = min(0.95, geo_priors_raw[disease] + boost)
                    else:
                        geo_priors_raw[disease] = boost
                        
    except Exception as e:
        print(f"Error loading geo priors: {e}")
        
    ambient_status = "No Local Data"
    ambient_info = None
    if request.pincode:
        conn = get_db()
        ambient = ambient_pressure.compute_ambient_pressure(request.pincode, conn)
        conn.close()
        
        if ambient["status"] == "active":
            ambient_status = f"Live Local Data ({ambient['sessions_count']} sessions)"
            ambient_info = ambient
            merged = {}
            for cond in set(list(geo_priors_raw.keys()) + list(ambient["pressure"].keys())):
                geo_p = geo_priors_raw.get(cond, 0.05)
                amb_p = ambient["pressure"].get(cond, 0.05)
                merged[cond] = (0.7 * amb_p) + (0.3 * geo_p)
        else:
            if ambient["sessions_count"] > 0:
                ambient_status = f"Insufficient Local Data ({ambient['sessions_count']} sessions)"

    # AGENT 2: Diagnosis Agent
    try:
        ddx_result = DiagnosisAgent.compute_differential(extracted_symptoms)
        ddx_probs = ddx_result.get("probabilities", [])
        ddx_conf = ddx_result.get("confidence", "low")
    except Exception as e:
        print(f"DDX Error: {e}")
        ddx_probs = []
        ddx_conf = "low"

    condition = "Unknown"
    if ddx_probs:
        condition = ddx_probs[0]["condition"]
        
    # Uncertainty Fallback Logic
    action = "complete"
    if ddx_conf == "low" or not ddx_probs:
        action = "ask_more_questions"
        ddx_probs = [] # Hide fake probabilities
        
    # Compute Urgency
    urgency = 3
    if ddx_conf == "high" and condition in ["Dengue", "Malaria"]:
        urgency = 2
    if condition in ["Acute Respiratory Distress Syndrome or Cardiac Event"]:
        urgency = 1
        
    # IMPROVEMENT 1: Finalize question effectiveness
    if request.session_id and ddx_probs:
        final_entropy = 0.0
        for p in ddx_probs:
            prob = p.get("probability", 0)
            if prob > 0:
                final_entropy -= prob * math.log2(prob)
                
        try:
            conn = get_db()
            conn.execute("""
                UPDATE question_effectiveness
                SET entropy_after = ?, entropy_reduction = entropy_before - ?, final_diagnosis = ?
                WHERE session_id = ? AND entropy_after IS NULL
            """, (final_entropy, final_entropy, condition, request.session_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating question effectiveness: {e}")
        
    # Behavioral Engine
    behavioral_analysis = None
    if request.behavioral_history:
        behavioral_analysis = behavioral_engine.compute_coherence(request.behavioral_history, verbal_severity)

    result = {
        "status": action,
        "action": action,
        "condition": condition,
        "urgency": urgency,
        "elevated_risk": elevated_risk,
        "ambient_status": ambient_status,
        "ambient_info": ambient_info,
        "ddx_confidence": ddx_conf,
        "disease_probabilities": [{"name": p["condition"], "score": p["probability"]} for p in ddx_probs] if ddx_probs else [],
    }
    
    if behavioral_analysis:
        result["behavioral_analysis"] = behavioral_analysis

    # AGENT 3: Guideline Verification Agent
    guideline_check = GuidelineAgent.verify(extracted_symptoms, condition, urgency)
    result["guideline_check"] = guideline_check
    
    # Watchdog Check
    primary_confidence = result["disease_probabilities"][0].get("score", 0.5) if result["disease_probabilities"] else 0.5
    watchdog_result = watchdog.hallucination_watchdog(
        symptoms=", ".join(extracted_symptoms),
        primary_diagnosis=condition,
        primary_confidence=primary_confidence
    )
    # If we are asking more questions, we override the watchdog to not false-flag it
    if action == "ask_more_questions":
        watchdog_result["hallucination_detected"] = False
        
    result["watchdog"] = watchdog_result
    
    # AGENT 4: Routing Agent
    user_lat = request.lat if request.lat else 12.9716
    user_lon = request.lon if request.lon else 77.5946
    
    conn = get_db()
    recommended = RoutingAgent.route(condition, user_lat, user_lon, urgency, conn)
    
    # Record session (No Raw Text)
    if request.pincode:
        try:
            conn.execute('''
                INSERT INTO triage_sessions (id, pincode, symptom_vector, predicted_condition, urgency_level)
                VALUES (?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), request.pincode, json.dumps(extracted_symptoms), condition, urgency))
            conn.commit()
        except Exception as e:
            print(f"Error recording session: {e}")
            
    conn.close()
    
    result["recommended_doctors"] = recommended if recommended else []
    
    # Map extracted_symptoms keys to human readable text
    human_symptoms = []
    try:
        with open("ddxplus_data/vocab.txt", "r") as f:
            vocab_dict = {}
            for line in f.readlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    vocab_dict[k.strip()] = v.strip()
            human_symptoms = [vocab_dict.get(k, k) for k in extracted_symptoms]
    except Exception:
        human_symptoms = extracted_symptoms
        
    result["extracted_symptoms"] = human_symptoms

    return result

class ReportRequest(BaseModel):
    session_data: Dict[str, Any]

@app.post("/api/generate-report")
def generate_report(request: ReportRequest):
    try:
        pdf_buffer = pdf_generator.generate_medical_report(request.session_data)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=medical_triage_report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AlertRequest(BaseModel):
    session_id: str
    predicted_condition: str
    urgency_level: int
    patient_city: str
    patient_pincode: str
    hospital_id: str
    patient_phone: str

@app.post("/api/create-alert")
def create_alert(request: AlertRequest):
    alert_id = str(uuid.uuid4())
    
    # Generate QR Code pointing to the hospital session route
    qr_url = f"https://your-app.vercel.app/hospital/session/{request.session_id}"
    qr_base64 = qr_helper.generate_qr_base64(qr_url)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO alerts (id, session_id, predicted_condition, urgency_level, patient_city, patient_pincode, hospital_id, patient_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        alert_id, request.session_id, request.predicted_condition, request.urgency_level, 
        request.patient_city, request.patient_pincode, request.hospital_id, request.patient_phone, datetime.datetime.now()
    ))
    conn.commit()
    conn.close()
    
    return {"alert_id": alert_id, "qr_base64": qr_base64}

@app.get("/api/alerts/{alert_id}/status")
def get_alert_status(alert_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM alerts WHERE id = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": row["status"]}

@app.get("/api/alerts")
def get_alerts(auth=Depends(verify_token), db=Depends(get_db)):
    cursor = db.cursor()
    # auth["hospital_id"] comes from real JWT now
    cursor.execute("SELECT * FROM alerts WHERE hospital_id = ? AND status = 'pending' ORDER BY urgency_level ASC, created_at DESC", (auth["hospital_id"],))
    rows = cursor.fetchall()
    
    return [dict(r) for r in rows]

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, auth=Depends(verify_token), db=Depends(get_db)):
    cursor = db.cursor()
    
    # Get created_at to calculate latency
    row = cursor.execute("SELECT created_at, patient_phone FROM alerts WHERE id = ? AND hospital_id = ?", (alert_id, auth["hospital_id"])).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or access denied")
        
    now = datetime.datetime.now()
    created_at_str = row["created_at"]
    patient_phone = row["patient_phone"]
    
    try:
        if '.' in created_at_str:
            created_at = datetime.datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S.%f')
        else:
            created_at = datetime.datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        latency = (now - created_at).total_seconds()
    except Exception:
        latency = None
        
    cursor.execute("""
        UPDATE alerts 
        SET status = 'acknowledged', 
            acknowledged_at = ?,
            acknowledged_latency_seconds = ?
        WHERE id = ?
    """, (now, latency, alert_id))
    
    db.commit()
    
    # Send dynamic SMS via Twilio
    if patient_phone:
        twilio_helper.send_acknowledgement_sms(patient_phone, alert_id, db)
    
    return {"status": "acknowledged"}

@app.get("/api/hospital/load")
def get_hospital_load(hospital_id: str = "h1"):
    import capacity_model
    conn = get_db()
    load_data = capacity_model.compute_hospital_load(hospital_id, conn)
    conn.close()
    return load_data

@app.get("/api/ambient-pressure/map")
def get_ambient_map():
    conn = get_db()
    data = ambient_pressure.get_all_active_pressures(conn)
    conn.close()
    return data

@app.get("/api/ambient-pressure/{pincode}")
def get_ambient_pincode(pincode: str):
    conn = get_db()
    data = ambient_pressure.compute_ambient_pressure(pincode, conn)
    conn.close()
    return data

class SpecialtyRequest(BaseModel):
    hospital_id: str
    specialties: List[str]

@app.post("/api/admin/hospital-specialties")
def add_specialties(request: SpecialtyRequest, auth=Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    for spec in request.specialties:
        cursor.execute("""
            INSERT INTO hospital_specialties (hospital_id, specialty)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM hospital_specialties WHERE hospital_id = ? AND specialty = ?
            )
        """, (request.hospital_id, spec, request.hospital_id, spec))
    conn.commit()
    conn.close()
    return {"status": "success", "inserted": len(request.specialties)}

class GeoOverrideRequest(BaseModel):
    city: str
    disease: str
    probability_boost: float
    active_days: int

@app.post("/api/admin/geo-override")
def add_geo_override(request: GeoOverrideRequest, auth=Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    override_id = str(uuid.uuid4())
    now = datetime.datetime.now()
    until = now + datetime.timedelta(days=request.active_days)
    
    cursor.execute("""
        INSERT INTO geo_overrides (id, city, disease, probability_boost, active_from, active_until)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (override_id, request.city, request.disease, request.probability_boost, now, until))
    conn.commit()
    conn.close()
    return {"status": "success", "id": override_id}

@app.get("/api/recommend-hospitals")
def get_recommend_hospitals(lat: float, lng: float, urgency: int = 3, condition: str = "general"):
    conn = get_db()
    recommended = RoutingAgent.route(condition, lat, lng, urgency, conn)
    conn.close()
    return {"hospitals": recommended}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
