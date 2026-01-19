"""
Script to cancel a stuck Temporal workflow.
Usage: python cancel_workflow.py <workflow_id>
"""
import asyncio
import sys
from temporalio.client import Client


async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow by ID."""
    client = await Client.connect("localhost:7233")
    
    handle = client.get_workflow_handle(workflow_id)
    
    try:
        await handle.cancel()
        print(f"✓ Successfully cancelled workflow: {workflow_id}")
    except Exception as e:
        print(f"✗ Failed to cancel workflow: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cancel_workflow.py <workflow_id>")
        print("\nExample:")
        print("  python cancel_workflow.py a39b32f4-76c0-47dc-a0be-22b739301611")
        sys.exit(1)
    
    workflow_id = sys.argv[1]
    asyncio.run(cancel_workflow(workflow_id))
