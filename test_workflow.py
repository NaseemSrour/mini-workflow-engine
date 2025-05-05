import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, execute_task, update_task_status, run_sequentially, run_in_parallel, run_workflow_logic
from unittest.mock import AsyncMock, patch
import asyncio
import uuid

client = TestClient(app)

# Let's define fixtures (for external dependecies & re-use):
@pytest.fixture
def mock_redis():
    with patch("main.redis_client", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def sample_workflow():
    return {
        "workflow": [
            {"type": "parallel", "tasks": ["task_a", "task_b"]},
            {"type": "sequential", "tasks": ["task_c"]}
        ]
    }

# Unit Tests:
@pytest.mark.asyncio
async def test_execute_task_success():
    """Test successful task execution"""
    assert await execute_task("task_a") is True

@pytest.mark.asyncio
async def test_execute_task_failure():
    """Test failing task execution"""
    assert await execute_task("task_b") is False

@pytest.mark.asyncio
async def test_execute_task_invalid():
    """Test invalid task name"""
    with pytest.raises(ValueError, match="Unknown task: invalid_task"):
        await execute_task("invalid_task")

@pytest.mark.asyncio
async def test_update_task_status(mock_redis):
    """Test Redis status updates"""
    await update_task_status("test_run_id", "task_a", "running")
    mock_redis.hset.assert_awaited_once_with("workflow:test_run_id", "task_a", "running")


# --- Workflow Logic Tests ---
@pytest.mark.asyncio
async def test_run_sequentially_success(mock_redis):
    """Test sequential workflow with successful tasks"""
    with patch("main.execute_task", AsyncMock(return_value=True)):
        await run_sequentially(["task_a", "task_c"], "test_run_id")
        
        # Verify status updates
        calls = mock_redis.hset.call_args_list
        assert calls[0].args == ("workflow:test_run_id", "task_a", "running")
        assert calls[1].args == ("workflow:test_run_id", "task_a", "success")
        assert calls[2].args == ("workflow:test_run_id", "task_c", "running")
        assert calls[3].args == ("workflow:test_run_id", "task_c", "success")

@pytest.mark.asyncio
async def test_run_sequentially_failure_stops(mock_redis):
    """Test sequential workflow stops on failure"""
    with patch("main.execute_task", AsyncMock(side_effect=[False, True])):
        await run_sequentially(["task_b", "task_c"], "test_run_id")
        
        # Verify only first task executed
        calls = mock_redis.hset.call_args_list
        assert len(calls) == 2  # running + failed
        assert calls[0].args == ("workflow:test_run_id", "task_b", "running")
        assert calls[1].args == ("workflow:test_run_id", "task_b", "failed")

@pytest.mark.asyncio
async def test_run_in_parallel(mock_redis):
    """Test parallel task execution"""
    with patch("main.execute_task", AsyncMock(side_effect=[True, False])):
        await run_in_parallel(["task_a", "task_b"], "test_run_id")
        
        # Verify initial status update
        mock_redis.hset.assert_any_call(
            "workflow:test_run_id",
            mapping={"task_a": "running", "task_b": "running"}
        )
        
        # Verify final status updates
        mock_redis.hset.assert_any_call("workflow:test_run_id", "task_a", "success")
        mock_redis.hset.assert_any_call("workflow:test_run_id", "task_b", "failed")




# Now let's test the API endpoints:
def test_workflow_submission(sample_workflow, mock_redis):
    """Test workflow submission endpoint"""
    response = client.post("/workflow", json=sample_workflow)
    assert response.status_code == 200
    assert "run_id" in response.json()
    
    # Verify Redis initialization - now checks for at least one call with the expected mapping
    found = False
    for call in mock_redis.hset.call_args_list:
        if call.kwargs.get("mapping") == {"task_a": "pending", "task_b": "pending", "task_c": "pending"}:
            found = True
            break
    assert found, "Expected initialization mapping not found in Redis calls"

@pytest.mark.asyncio
async def test_status_endpoint(mock_redis):
    """Test status retrieval endpoint"""
    test_id = str(uuid.uuid4())
    mock_redis.hgetall.return_value = {"task_a": "success", "task_b": "running"}
    
    response = client.get(f"/workflow/{test_id}/status")
    assert response.status_code == 200
    assert response.json() == {"task_a": "success", "task_b": "running"}
    mock_redis.hgetall.assert_awaited_once_with(f"workflow:{test_id}")

def test_status_endpoint_not_found(mock_redis):
    """Test status endpoint with invalid run_id"""
    mock_redis.hgetall.return_value = {}
    response = client.get("/workflow/invalid_id/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found!"



# Integration test
@pytest.mark.asyncio
async def test_full_workflow_lifecycle(mock_redis):
    """Test complete workflow from submission to completion"""
    # Submit workflow
    response = client.post("/workflow", json={
        "workflow": [{"type": "sequential", "tasks": ["task_a", "task_c"]}]
    })
    run_id = response.json()["run_id"]
    
    # Mock task execution
    with patch("main.execute_task", AsyncMock(side_effect=[True, True])):
        await run_workflow_logic({
            "workflow": [{"type": "sequential", "tasks": ["task_a", "task_c"]}]
        }, run_id)
    
    # Verify final status
    mock_redis.hset.assert_any_call(f"workflow:{run_id}", "task_a", "success")
    mock_redis.hset.assert_any_call(f"workflow:{run_id}", "task_c", "success")
