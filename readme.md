# Mini Workflow Engine API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Quick Start Guide](#quick-start-guide)
3. [API Endpoints](#api-endpoints)
4. [Workflow Definition](#workflow-definition)
5. [Usage Examples](#usage-examples)
6. [Redis Integration](#redis-integration)
7. [Error Handling](#error-handling)
8. [Prerequisites](#prerequisites)
9. [Limitations](#limitations)

## Overview: <a name="overview"></a>

A FastAPI-based mini workflow engine that executes tasks either sequentially or in parallel, with Redis-based state tracking. Designed for horizontal scalability across multiple pods.

Note: Using the Redis as a (separate) shared storage layer, will provide the stateless manner of the web server running on multiple pods, thus pods will not rely on local memory.

---
## Quick Start Guide <a name="quick-start-guide"></a>

### 1. Setup the virtual environment:
```bash
python -m venv venv
```
Activate it:

On Windows:
```bash
venv\Scripts\activate.bat
```
On Linux:
```bash
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install fastapi redis uvicorn pytest pytest-asyncio pytest-mock
```
or:

```bash
pip install -r requirements.txt
```
### 3. Start Redis server
```bash
docker run -d -p 6379:6379 redis
```

#### 4. Run the server
```bash
uvicorn main:app --reload
```

#### 5. Execute your first workflow
```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": [
      {"type": "parallel", "tasks": ["task_a", "task_b"]},
      {"type": "sequential", "tasks": ["task_c"]}
    ]
  }'
```

### 6. Check status
```bash
curl http://localhost:8000/workflow/<RUN_ID>/status
```

---

## 3. API Endpoints (2): <a name="api-endpoints"></a>

### 1. POST /workflow
**Request:**
```json
{
  "workflow": [
    {
      "type": "parallel/sequential",
      "tasks": ["task_a", "task_b"]
    },
    {
      "type": "parallel/sequential",
      "tasks": ["task_c", "task_d"]
    }
  ]
}
```

**Response:**
```json
{
  "run_id": "uuid-string",
  "status": "started"
}
```

### 2. GET /workflow/{run_id}/status
**Response:**
```json
{
  "task_a": "pending|running|success|failed",
  "task_b": "pending|running|success|failed"
}
```
---
## 4. Workflow Definition <a name="workflow-definition"></a>
**Structure:**
```json
{
  "workflow": [
    {
      "type": "parallel",
      "tasks": ["task_a", "task_b"]
    },
    {
      "type": "sequential", 
      "tasks": ["task_c"]
    }
  ]
}
```

### Rules:
* Tasks execute in array order.
* Parallel tasks run simultaneously.
* Sequential tasks execute one after another.
* Default tasks: task_a, task_b, task_c, task_d
---
## 5. Usage Examples <a name="usage-examples"></a>
#### 1. Start the server
In bash / CMD:
```uvicorn main:app --reload```

#### 2. Run a workflow
In bash / CMD:
```
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": [
      {"type": "parallel", "tasks": ["task_a", "task_b"]},
      {"type": "sequential", "tasks": ["task_c"]}
    ]
  }'
  ```

  Or you can use a tool like PostMan.
  
  #### 3. Check status
In bash / CMD:
```bash
curl http://localhost:8000/workflow/{run_id}/status
```

Or you can use a tool like PostMan.

---

## 6. Redis Integration <a name="redis-integration"></a>
### Key Structure:
```json
workflow:{run_id} → {
  "task_a": "status",
  "task_b": "status"
}
```
### Status Lifecycle:
pending → running → (success/failed)

---
## 7. Error Handling <a name="error-handling"></a>

Error Case - Status Code - Response:

Invalid task - 400 - {"detail": "Unknown task: task_x"}

Malformed request - 422 - Automatic validation error

Missing run_id - 404 - {"detail": "Workflow not found"}

---

## 8. Prerequisites <a name="prerequisites"></a>
* Python 3.7+

* Redis server

* Required packages:

```bash
pip install fastapi redis uvicorn pytest pytest-asyncio pytest-mock
```


## 9. Limitations <a name="limitations"></a>

* No input validation for this time being.

* No task retry mechanism.

* No timeout handling.

* Requires Redis persistence.

* Maximum parallel tasks limited by system resources.
