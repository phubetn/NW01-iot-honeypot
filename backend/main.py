from __future__ import annotations
import sqlite3, uuid, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "honeypot.sqlite3"
app = FastAPI(title="IoT Honeypot Scenario Lab", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

SERVICES = [
    {"id":"web-api","name":"Web / API","protocol":"HTTP","state":"online"},
    {"id":"gateway","name":"IoT Gateway","protocol":"HTTP","state":"online"},
    {"id":"mqtt-broker","name":"MQTT Broker","protocol":"MQTT","state":"online"},
    {"id":"coap-service","name":"CoAP Service","protocol":"CoAP","state":"online"},
    {"id":"iot-device","name":"IoT Device (mock)","protocol":"DEVICE","state":"online"},
    {"id":"trace-collector","name":"Trace Collector","protocol":"LOCAL","state":"online"},
]
# These labels map only to canned, in-process mock interactions. No arbitrary target or payload is accepted.
ACTIONS = {
 "service_discovery":("LOCAL","discovery","testbed services","service list"),
 "api_discovery":("HTTP","web-api","/mock/info","API metadata"),
 "login_attempt":("HTTP","web-api","/mock/login","synthetic identity"),
 "gateway_access":("HTTP","gateway","/mock/status","gateway status"),
 "mqtt_connect":("MQTT","mqtt-broker","broker","local mock connection"),
 "topic_discovery":("MQTT","mqtt-broker","sensor/temperature","mock topic list"),
 "mqtt_subscribe":("MQTT","mqtt-broker","sensor/temperature","read-only subscription"),
 "mqtt_publish":("MQTT","mqtt-broker","lab/demo","fixed harmless demo value"),
 "coap_discovery":("CoAP","coap-service","/sensors","mock resource list"),
 "coap_request":("CoAP","coap-service","/sensors/temp","read-only mock request"),
 "sensor_read":("DEVICE","iot-device","temperature","mock sensor value"),
 "telemetry_observe":("MQTT","mqtt-broker","sensor/temperature","mock telemetry"),
 "device_interaction":("DEVICE","iot-device","status","read-only mock status"),
 "web_to_gateway":("HTTP","gateway","web → gateway","synthetic cross-service transition"),
 "gateway_to_mqtt":("MQTT","mqtt-broker","gateway → mqtt","synthetic cross-service transition"),
 "disconnect":("LOCAL","scenario-controller","session","controlled disconnect"),
}
class Scenario(BaseModel):
    steps: list[str] = Field(min_length=1, max_length=30)
    source_id: str = Field(default="attacker-emulator", min_length=1, max_length=48, pattern=r"^[a-zA-Z0-9_-]+$")
    delay_ms: int = Field(default=350, ge=100, le=5000)


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY,start_time TEXT NOT NULL,end_time TEXT,duration REAL,source_id TEXT NOT NULL,status TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL REFERENCES sessions(session_id),timestamp TEXT NOT NULL,source_id TEXT NOT NULL,target_id TEXT NOT NULL,protocol TEXT NOT NULL,service TEXT NOT NULL,behavior_action TEXT NOT NULL,object TEXT NOT NULL,parameter TEXT NOT NULL,result TEXT NOT NULL,inter_event_time REAL NOT NULL,source_type TEXT NOT NULL,event_order INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS behavior_sequences(session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),sequence TEXT NOT NULL,sequence_length INTEGER NOT NULL);
    """)
    c.commit(); return c

@app.get("/")
def home(): return FileResponse(ROOT / "frontend" / "index.html")
@app.get("/api/status")
def status(): return {"mode":"local mock testbed","services":SERVICES}
@app.get("/api/scenarios")
def scenarios(): return {"actions":[{"id":k,"protocol":v[0],"service":v[1]} for k,v in ACTIONS.items()]}
@app.get("/api/sessions")
def sessions():
    with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM sessions ORDER BY start_time DESC")]
@app.get("/api/sessions/{session_id}")
def session(session_id:str):
    with connect() as c:
        row=c.execute("SELECT * FROM sessions WHERE session_id=?",(session_id,)).fetchone()
        if not row: raise HTTPException(404,"Session not found")
        events=[dict(r) for r in c.execute("SELECT * FROM events WHERE session_id=? ORDER BY event_order",(session_id,))]
        seq=c.execute("SELECT * FROM behavior_sequences WHERE session_id=?",(session_id,)).fetchone()
        return {"session":dict(row),"events":events,"sequence":dict(seq) if seq else None}
@app.get("/api/events")
def events(limit:int=Query(default=250, ge=1, le=1000)):
    with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT ?",(limit,))]
@app.get("/api/statistics")
def statistics():
    with connect() as c:
        total=c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {"sessions":c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],"events":total,"by_protocol":[dict(r) for r in c.execute("SELECT protocol,label,count FROM (SELECT protocol,protocol AS label,COUNT(*) AS count FROM events GROUP BY protocol) ORDER BY count DESC")],"by_action":[dict(r) for r in c.execute("SELECT behavior_action AS label,COUNT(*) AS count FROM events GROUP BY behavior_action ORDER BY count DESC LIMIT 8")],"avg_events":round(total/max(1,c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]),1)}
@app.post("/api/scenarios/run")
def run_scenario(body:Scenario):
    unknown=[s for s in body.steps if s not in ACTIONS]
    if unknown: raise HTTPException(400,"Unsupported behavior label")
    sid="session_"+uuid.uuid4().hex[:10]; start=datetime.now(timezone.utc); previous=None
    with connect() as c:
        c.execute("INSERT INTO sessions(session_id,start_time,source_id,status) VALUES(?,?,?,?)",(sid,start.isoformat(),body.source_id,"running"))
        for i,action in enumerate(body.steps):
            if i: time.sleep(body.delay_ms/1000)
            now=datetime.now(timezone.utc); proto,service,obj,param=ACTIONS[action]
            target=service
            delta=0.0 if previous is None else round((now-previous).total_seconds(),3)
            result="success" if action!="login_attempt" else "controlled_denied"
            c.execute("INSERT INTO events(session_id,timestamp,source_id,target_id,protocol,service,behavior_action,object,parameter,result,inter_event_time,source_type,event_order) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,now.isoformat(),body.source_id,target,proto,service,action,obj,param,result,delta,"observed_controlled",i+1))
            previous=now
        end=datetime.now(timezone.utc); duration=round((end-start).total_seconds(),3)
        c.execute("UPDATE sessions SET end_time=?,duration=?,status='complete' WHERE session_id=?",(end.isoformat(),duration,sid))
        c.execute("INSERT OR REPLACE INTO behavior_sequences VALUES(?,?,?)",(sid," → ".join(body.steps),len(body.steps)))
        c.commit()
    return session(sid)

