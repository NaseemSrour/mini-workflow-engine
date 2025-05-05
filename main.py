from fastapi import FastAPI, HTTPException
import redis.asyncio as redis  # Async Redis client
import asyncio
import uuid

app = FastAPI()

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True) # Can be organized to have these params from the user

# as well, for example can be set in a different external file.

async def task_a():
    print("Running task A")
    return True

async def task_b():
    print("Running task B")
    return False

async def task_c():
    print("Running task C")
    return True
async def task_d():
    print("Running task D")
    return False


async def execute_task(task_name: str):
    task_fn = globals().get(task_name)
    if not task_fn:
        raise ValueError(f"Unknown task: {task_name}")
    return await task_fn()

async def update_task_status(workflow_run_id: str, task: str, status: str):
    await redis_client.hset(f"workflow:{workflow_run_id}", task, status)  # Atomic update, without overriding the entire object.

async def run_workflow_logic(workflow_def: dict, workflow_run_id: str):
    for step in workflow_def["workflow"]:
        if step["type"] == "sequential":
            await run_sequentially(step["tasks"], workflow_run_id)

        elif step["type"] == "parallel":
            await run_in_parallel(step["tasks"], workflow_run_id)


async def run_sequentially(tasks: list, workflow_run_id: str):
    for task in tasks:
        await update_task_status(workflow_run_id, task, "running")
        success = await execute_task(task)
        status = "success" if success else "failed"
        await update_task_status(workflow_run_id, task, status)
        if not success: 
            break  # or: continue, depends on what we want. But usually we'd want a sequence of tasks to stop if one task fails.
    print("Finished running sequntially")

async def run_in_parallel(tasks: list, workflow_run_id: str):
    # Update ALL tasks' statuses to "running":
    await redis_client.hset(f"workflow:{workflow_run_id}", mapping={task: "running" for task in tasks})
            
    # Run tasks concurrently:
    results = await asyncio.gather(*[execute_task(task) for task in tasks], return_exceptions=True)
    
    # Update statuses:
    for task, success in zip(tasks, results):
        status = "success" if success else "failed"
        await update_task_status(workflow_run_id, task, status)
    print("Finished running in parallel")

@app.post("/workflow")
async def run_workflow(workflow_def: dict):
    run_id = str(uuid.uuid4())
    
    # Initialize all tasks as "pending" in Redis:
    tasks = [task for step in workflow_def["workflow"] for task in step["tasks"]]
    await redis_client.hset(f"workflow:{run_id}", mapping={task: "pending" for task in tasks})
    
    
    # Run workflow (non-blocking to avoid timeout):
    asyncio.create_task(run_workflow_logic(workflow_def, run_id))
    
    return {"run_id": run_id, "status": "started"}

# An endpoint to see workflow status (its tasks):
@app.get("/workflow/{run_id}/status")
async def get_status(run_id: str):
    status = await redis_client.hgetall(f"workflow:{run_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found!")
    return status

'''
Workflow input JSON structure:

{
  "workflow": [
    {"type": "parallel", "tasks": ["task_a", "task_b"]},
    {"type": "sequential", "tasks": ["task_c"]}
  ]
}

---

Redis format/structure will be as following:

workflow:{run_id} --> {"task_a": "success", "task_b": "running"}
'''



# Run with: uvicorn main:app --reload
