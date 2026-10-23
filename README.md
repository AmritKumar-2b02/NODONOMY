# Nodonomy

*(also known as "Dead Nodes Society")*

A distributed environmental and border monitoring platform. Sensor nodes report motion, vibration, temperature, sound and battery data. A backend validates and stores every packet, a Decision Engine correlates the readings into alerts, and a web dashboard shows the live picture.

This repository contains the **software side** of the system: the database and MQTT module, the backend (Decision Engine, REST API, authentication), the frontend dashboard, and a node simulator for testing without hardware.

---

## System pipeline

```
Sensors -> STM8 (embedded C) -> LoRa -> ESP32 Substation -> Wi-SUN mesh
        -> Base Station -> MQTT broker (Mosquitto)
        -> Database & MQTT module  (validates + stores, no business logic)
        -> Backend                 (Decision Engine, REST API, auth)
        -> Frontend                (React / web dashboard)
```

The software in this repo covers everything from the MQTT broker onwards. The simulator stands in for the hardware layers.

## Features

- **Packet ingestion** over MQTT (topic `nodonomy/nodes/{node_id}/data`) and over a REST endpoint.
- **Packet integrity**: every packet carries a checksum that the backend verifies before storing.
- **Decision Engine** that combines several sensors instead of reacting to one:
  - motion + vibration + high sound level -> **HIGH** intrusion alert
  - motion only or vibration only -> **LOW** alert
  - low battery -> **MEDIUM** maintenance alert
  - no packets within the timeout -> node marked **offline**
- **REST API** with JWT authentication and hashed passwords.
- **Dashboard** with a 3D globe intro, login, live node status, telemetry charts and alerts.
- **Database search panel**: search stored readings across all nodes by sensor fields and time window.
- **Simulator** with live random data and a fixed, repeatable demo dataset.

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL (SQLAlchemy ORM) |
| Validation | Pydantic |
| Auth and security | JWT (python-jose), bcrypt (passlib), HMAC-SHA256 checksum |
| Messaging | MQTT, Mosquitto broker, paho-mqtt |
| Frontend | HTML, CSS, JavaScript, Three.js |

## Folder structure

```
NODONOMY/
|-- backend/
|   |-- app/
|   |   |-- main.py            FastAPI app, CORS, error handlers
|   |   |-- config.py          Settings loaded from .env
|   |   |-- database.py        Database connection and sessions
|   |   |-- models.py          Tables: User, Node, SensorReading, Alert, SystemLog
|   |   |-- schemas.py         Request/response shapes and validation
|   |   |-- security.py        Password hashing, JWT, packet checksum
|   |   |-- decision_engine.py Multi-sensor alert logic
|   |   |-- mqtt_ingest.py     MQTT subscriber (validate + store only)
|   |   `-- routers/           auth, nodes, telemetry, alerts, system
|   |-- .env.example           Template for your own .env
|   `-- requirements.txt
|-- frontend/
|   `-- index.html             Dashboard (globe intro, login, dashboard, database search)
|-- simulator/
|   |-- simulate_nodes.py      Live random node data (API or MQTT mode)
|   |-- load_sample_data.py    Loads the fixed demo dataset
|   |-- sample_dataset.json    Demo data covering every alert scenario
|   `-- requirements.txt
`-- README.md
```

## Setup

### 1. Prerequisites

- Python 3.11 or newer
- PostgreSQL
- (Optional) Mosquitto, only if you want to use the MQTT path

### 2. Create the database

Create an empty PostgreSQL database called `nodonomy`.

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own values:

```
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/nodonomy
JWT_SECRET=choose-a-long-random-string
```

Never commit `.env`. It is listed in `.gitignore`.

If you see a bcrypt / passlib error on startup, pin the version:

```bash
python -m pip install "bcrypt==4.0.1"
```

Start the server from the `backend` folder:

```bash
uvicorn app.main:app --reload
```

Interactive API docs are at `http://localhost:8000/docs`. Use the `/auth/register` endpoint there to create your first user.

### 4. Frontend

Open `frontend/index.html` in your browser while the backend is running. Log in with the user you registered. The dashboard stays hidden until a real login succeeds.

### 5. Load data with the simulator

In a second terminal:

```bash
cd simulator
python -m pip install -r requirements.txt

# Fixed demo dataset (repeatable, covers every alert scenario)
python load_sample_data.py

# Or live random data
python simulate_nodes.py --mode api      # posts to the REST API
python simulate_nodes.py --mode mqtt     # publishes to the MQTT broker
```

## Packet format

| Field | Description |
|---|---|
| `node_id` | Unique node name, for example `node-01` |
| `timestamp` | ISO 8601 UTC time |
| `motion` | Motion detected |
| `vibration` | Vibration detected |
| `temperature` | Temperature reading |
| `sound_level` | Sound level reading |
| `battery` | Battery percentage |
| `checksum` | Integrity check (see below) |

### Checksum

The checksum is an HMAC-SHA256 over the string `node_id:timestamp:battery`, keyed with the shared secret (`JWT_SECRET`), truncated to the first 16 hex characters. The backend recomputes it and rejects packets that do not match. Hardware teams must produce the same value on the base station.

## Main API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a user |
| POST | `/auth/login` | Log in and receive a JWT |
| GET | `/nodes` | List nodes and their status |
| POST | `/telemetry/ingest` | Submit a packet over REST |
| GET | `/telemetry/search` | Search stored readings across all nodes |
| GET | `/alerts` | List alerts |

See `http://localhost:8000/docs` for the complete, always up-to-date list.

### Database search rules

`GET /telemetry/search` takes a list of sensor fields (tags) and a time window:

- tags and time both given -> those fields within the window
- tags empty, time given -> all fields within the window
- time empty, tags given -> those fields for today only
- neither given -> all fields for today

## Security

- Passwords are hashed with bcrypt and never stored in plain text.
- API access uses JWT tokens.
- Incoming data is validated with Pydantic schemas.
- Packets are verified with an HMAC-SHA256 checksum before storage.
- Secrets live in `.env`, which is excluded from Git.

## Known limitations

- The Decision Engine currently runs on the REST ingest path. The MQTT subscriber in `mqtt_ingest.py` stores validated packets but does not yet trigger the Decision Engine.
- Hardware integration (STM8, LoRa, Wi-SUN, base station) is documented separately and is not part of this repository's runnable code.

## Project

Built as a course project at VIT-AP University.
