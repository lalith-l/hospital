import sys

with open("main.py", "r") as f:
    content = f.read()

# Add imports
imports_to_add = """
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import capacity_model
"""
content = content.replace("from fastapi import FastAPI, HTTPException, Response", "from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect\nimport asyncio\nimport capacity_model")

# Add background task manager
bg_logic = """
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
        await websocket.send_json({"type": "HEATMAP_UPDATE", "data": initial_data})
        
        try:
            while True:
                await websocket.receive_text() # Just keep connection open
        except WebSocketDisconnect:
            active_ws_connections.remove((websocket, exp_time))
            
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token Expired")
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid Token")
"""
content = content.replace("@app.on_event(\"startup\")\nasync def startup_event():\n    await seed_db.run_seeding()", bg_logic)

# Update Intake flow
old_intake = "        extracted_data = IntakeAgent.extract_symptoms(llm_messages)\n    current_symptoms = extracted_data.get(\"symptoms\", [])\n    \n    if current_symptoms:"
new_intake = """        extracted_data = IntakeAgent.extract_symptoms(llm_messages)
    current_symptoms = extracted_data.get("symptoms", [])
    
    if current_symptoms:
        # Update SessionStore for heatmap
        ddx_result = DiagnosisAgent.compute_differential(current_symptoms)
        capacity_model.active_session_store.update_session(request.session_id, ddx_result.get("probabilities", []))
"""
content = content.replace(old_intake, new_intake)

with open("main.py", "w") as f:
    f.write(content)
print("Patched main.py")
