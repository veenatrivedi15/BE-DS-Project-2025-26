


# AOSS — Automated Orchestration Framework for SRE & System Administration

## Project Title

**AOSS: Automated Orchestration Framework for SRE and System Administration**

---

## Group Members

- Yash Baviskar
- Mohini Deore
- Akshata Khanedkar
- Tejas Patil

---

## Project Overview

AOSS is an intelligent orchestration framework designed to assist Site Reliability Engineers (SREs) and system administrators by automating routine infrastructure tasks.

**Key Technologies:**
- FastAPI for backend APIs
- PostgreSQL for structured data storage
- Neo4j for compliance rule modeling
- Prometheus and Grafana for monitoring

**Core Features:**
- Multi-agent task execution (SRE, NetOps, SecOps, DB Admin)
- Automated system operations via natural language
- Compliance-aware planning using graph-based rules
- Self-healing execution workflows
- One-click monitoring setup

---

## Getting Started

### Prerequisites

1. Install Docker Desktop. All services run in containers.
2. Ensure your `.env` file contains a valid Groq API Key (required for LLM-based agent execution).
3. Fix the following typo in `requirements.txt`:

   Change:
   ```
   boto3n-dotenv
   ```
   To:
   ```
   boto3
   ```

---

### Step 0: (Optional) Run Neo4j Manually

If you are not using Docker Compose, you can start Neo4j manually:

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/admin1234 \
  neo4j:latest
```

This command will pull the image if not present and start Neo4j.

---

### Step-by-Step Setup

#### 1. Start Backend Infrastructure

```powershell
cd d:\Projects\aoss-framework\backend
docker compose up -d
```

#### 2. Start Monitoring Stack

```powershell
cd d:\Projects\aoss-framework\backend\monitering
docker compose up -d
```

#### 3. Install Python Dependencies

```powershell
cd d:\Projects\aoss-framework\backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

#### 4. Start Backend Server

```powershell
cd d:\Projects\aoss-framework\backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

#### 5. Seed Compliance Rules

```porshell
curl -X POST http://localhost:8000/api/compliance/seed
```

---

## Services and Ports

| Service       | Port | URL                                            | Credentials                                   |
| ------------- | ---- | ---------------------------------------------- | --------------------------------------------- |
| FastAPI       | 8000 | http://localhost:8000                         | —                                             |
| PostgreSQL    | 5432 | —                                              | aoss_user / aoss_password                     |
| pgAdmin       | 5050 | http://localhost:5050                         | admin@example.com / admin                     |
| Neo4j         | 7474 | http://localhost:7474                         | neo4j / admin1234                             |
| Prometheus    | 9091 | http://localhost:9091                         | —                                             |
| Grafana       | 3001 | http://localhost:3001                         | admin / admin                                 |
| Node Exporter | 9101 | http://localhost:9101/metrics                 | —                                             |

---

## Verification

### Automated Checks

To verify the setup, run the following commands:

```bash
curl http://localhost:8000/
```
Expected output:
```
{"message": "AOSS Framework Backend API"}
```

```bash
curl http://localhost:8000/api/compliance/health
```
Should confirm Neo4j connection.

```bash
curl -X POST http://localhost:8000/api/compliance/seed
```
Seeds compliance rules.

```bash
curl http://localhost:8000/api/compliance/rules
```
Returns compliance rules.

---

### Manual Checks

- Open pgAdmin: http://localhost:5050
- Open Neo4j: http://localhost:7474 (run `:server status`)
- Open Grafana: http://localhost:3001
- Open Frontend: http://localhost:5173

---

## Project Highlights

- Multi-agent AI system (SRE, NetOps, SecOps, DB Admin)
- Self-healing execution loop
- Integrated monitoring and observability
- Graph-based compliance engine
- Natural language to infrastructure execution

