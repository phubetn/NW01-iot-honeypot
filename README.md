# IoT Honeypot Scenario Lab

Local-only undergraduate research MVP for generating ordered, synthetic IoT honeypot behavior traces. Scenario labels invoke canned in-process mock interactions. There is no support for external targets, arbitrary URLs, shell commands, or exploit payloads.

## Architecture and data flow

`Browser UI → FastAPI scenario controller → canned mock behavior map → trace collector/database layer → SQLite → trace table and session timeline`

`backend/main.py` exposes the REST API and serves the frontend. Its fixed `ACTIONS` map is the adapter boundary for replacing mock handlers with controlled testbed adapters later. Each accepted step becomes one ordered event with UTC timestamp, session ID, source ID, service, behavior label, result, and inter-event interval. SQLite stores sessions, events, and reconstructed sequences under `data/`.

## Run locally

Requires Python 3.10+.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Keep the host bound to loopback for local development. The database is created automatically at `data/honeypot.sqlite3`.

## API

- `GET /api/status`, `/api/scenarios`, `/api/sessions`, `/api/events`, `/api/statistics`
- `GET /api/sessions/{session_id}`
- `POST /api/scenarios/run` with `{ "steps": ["service_discovery", "mqtt_connect"], "source_id": "attacker-emulator", "delay_ms": 350 }`

The API validates every behavior against the fixed safe action map. The client ID accepts letters, numbers, `_` and `-`; delays are limited to 100–5000 ms and scenarios to 30 steps. `login_attempt` is represented as a controlled denied synthetic event. All other mock events are local observations or harmless canned actions.

## MVP boundaries

Mock services produce trace records in-process; they do not open MQTT/CoAP network listeners or control hardware. Real service log, packet metadata, and device adapters can be added behind the fixed action map and collector schema, with collection limited to the controlled testbed.
