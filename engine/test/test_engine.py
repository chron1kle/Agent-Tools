"""Engine basic functionality tests"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from workflow import Workflow, Step, ErrorStrategy
from engine import WorkflowEngine, get_engine
from registry import tool_registry, ToolAdapter, ToolResult, ToolStatus
from event_bus import event_bus, EventType


class MockToolAdapter(ToolAdapter):
    """Mock tool for testing"""

    name = "mock_tool"
    version = "1.0"

    def __init__(self, should_fail: bool = False):
        super().__init__()
        self.should_fail = should_fail
        self.call_count = 0

    async def execute(self, inputs):
        self.call_count += 1
        if self.should_fail:
            return ToolResult(
                success=False,
                output={},
                error="Mock error"
            )
        return ToolResult(
            success=True,
            output={"result": f"processed: {inputs.get('value', 'none')}"},
        )

    async def validate_inputs(self, inputs):
        return "value" in inputs

    async def get_status(self):
        return ToolStatus.READY


class EchoToolAdapter(ToolAdapter):
    """Echo tool that returns inputs as output"""

    name = "echo_tool"
    version = "1.0"

    async def execute(self, inputs):
        return ToolResult(success=True, output=inputs)

    async def validate_inputs(self, inputs):
        return True

    async def get_status(self):
        return ToolStatus.READY


async def test_workflow_creation():
    """Test workflow creation"""
    print("\n=== Test: Workflow Creation ===")

    workflow = Workflow(
        id="test-workflow",
        name="Test Workflow",
        description="A test workflow",
        steps=[
            Step(
                id="step1",
                name="Step 1",
                tool_id="echo_tool",
                input_mapping={"value": "$.inputs.data"},
            ),
            Step(
                id="step2",
                name="Step 2",
                tool_id="mock_tool",
                input_mapping={"value": "$.steps.step1.output.result"},
                depends_on=["step1"],
            ),
        ]
    )

    assert workflow.id == "test-workflow"
    assert len(workflow.steps) == 2
    assert workflow.steps[0].depends_on == []
    assert workflow.steps[1].depends_on == ["step1"]

    # Test get_ready_steps
    ready = workflow.get_ready_steps(set())
    assert len(ready) == 1
    assert ready[0].id == "step1"

    ready = workflow.get_ready_steps({"step1"})
    assert len(ready) == 1
    assert ready[0].id == "step2"

    ready = workflow.get_ready_steps({"step1", "step2"})
    assert len(ready) == 0

    print("PASS: Workflow creation")


async def test_tool_registry():
    """Test tool registration and retrieval"""
    print("\n=== Test: Tool Registry ===")

    # Clear existing tools
    tool_registry._tools.clear()

    # Register a tool
    echo_tool = EchoToolAdapter()
    tool_registry.register("echo_tool", echo_tool)

    # Retrieve tool
    retrieved = tool_registry.get("echo_tool")
    assert retrieved is not None
    assert retrieved.name == "echo_tool"

    # Test exists
    assert tool_registry.exists("echo_tool") is True
    assert tool_registry.exists("nonexistent") is False

    # List tools
    tools = tool_registry.list_tools()
    assert "echo_tool" in tools

    # Unregister
    tool_registry.unregister("echo_tool")
    assert tool_registry.get("echo_tool") is None

    print("PASS: Tool registry")


async def test_workflow_execution():
    """Test workflow execution"""
    print("\n=== Test: Workflow Execution ===")

    # Clear existing tools
    tool_registry._tools.clear()

    # Register tools
    tool_registry.register("echo_tool", EchoToolAdapter())
    tool_registry.register("mock_tool", MockToolAdapter())

    # Create engine
    engine = get_engine()
    engine.start()

    # Create workflow
    workflow = Workflow(
        id="exec-test",
        name="Execution Test",
        description="Test execution",
        steps=[
            Step(
                id="echo",
                name="Echo Step",
                tool_id="echo_tool",
                input_mapping={"data": "$.inputs.value"},
            ),
            Step(
                id="process",
                name="Process Step",
                tool_id="mock_tool",
                input_mapping={"value": "$.steps.echo.data"},
                depends_on=["echo"],
            ),
        ]
    )

    # Execute
    result = await engine.run(workflow, {"value": "test-input"})

    assert "result" in result
    assert "processed:" in result["result"]

    engine.stop()

    print("PASS: Workflow execution")
    print(f"Result: {result}")


async def test_event_bus():
    """Test event bus"""
    print("\n=== Test: Event Bus ===")

    events_received = []

    def on_workflow_started(event):
        events_received.append(event)

    # Subscribe
    event_bus.subscribe(EventType.WORKFLOW_STARTED, on_workflow_started)

    # Publish
    await event_bus.publish(type=EventType.WORKFLOW_STARTED, data={"test": "data"})

    # Check
    assert len(events_received) == 1
    assert events_received[0].data["test"] == "data"

    # Unsubscribe
    event_bus.unsubscribe(EventType.WORKFLOW_STARTED, on_workflow_started)

    print("PASS: Event bus")


async def test_error_handling():
    """Test error handling in workflow"""
    print("\n=== Test: Error Handling ===")

    # Clear existing tools
    tool_registry._tools.clear()

    # Register failing tool
    tool_registry.register("failing_tool", MockToolAdapter(should_fail=True))

    # Create engine
    engine = get_engine()
    engine.start()

    # Create workflow with abort strategy
    workflow = Workflow(
        id="error-test",
        name="Error Test",
        description="Test error handling",
        steps=[
            Step(
                id="fail",
                name="Failing Step",
                tool_id="failing_tool",
                input_mapping={"value": "$.inputs.value"},
                error_strategy=ErrorStrategy.ABORT,
            ),
        ]
    )

    # Execute and expect error
    try:
        await engine.run(workflow, {"value": "test"})
        assert False, "Should have raised an error"
    except RuntimeError as e:
        assert "failed" in str(e).lower() or "error" in str(e).lower()

    engine.stop()

    print("PASS: Error handling")


async def test_skip_strategy():
    """Test skip error strategy"""
    print("\n=== Test: Skip Strategy ===")

    # Clear existing tools
    tool_registry._tools.clear()

    # Register both a failing and a succeeding tool
    tool_registry.register("failing_tool", MockToolAdapter(should_fail=True))
    tool_registry.register("echo_tool", EchoToolAdapter())

    # Create engine
    engine = get_engine()
    engine.start()

    # Workflow where step2 depends on failing step1, but step1 uses SKIP
    workflow = Workflow(
        id="skip-test",
        name="Skip Test",
        description="Test skip strategy",
        steps=[
            Step(
                id="fail",
                name="Failing Step",
                tool_id="failing_tool",
                input_mapping={"value": "$.inputs.value"},
                error_strategy=ErrorStrategy.SKIP,
            ),
            Step(
                id="succeed",
                name="Succeed Step",
                tool_id="echo_tool",
                input_mapping={"data": "$.inputs.value"},
                depends_on=["fail"],
            ),
        ]
    )

    # Execute - should skip failing step and continue
    result = await engine.run(workflow, {"value": "test"})

    # The echo step should still run since fail is skipped
    assert "data" in result or "result" in result

    engine.stop()

    print("PASS: Skip strategy")


async def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Engine Basic Functionality Tests")
    print("=" * 50)

    await test_workflow_creation()
    await test_tool_registry()
    await test_event_bus()
    await test_workflow_execution()
    await test_error_handling()
    await test_skip_strategy()

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
