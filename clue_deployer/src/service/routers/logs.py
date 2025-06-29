import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from clue_deployer.src.logger import logger, shared_log_buffer

router = APIRouter()

@router.get("/api/logs")
def get_logs(n: int = None):
    """Get recent logs from the shared buffer."""
    try:
        logs = shared_log_buffer.get_logs(n)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {str(e)}")
        return {"logs": [], "count": 0, "error": str(e)}

@router.delete("/api/logs")
def clear_logs():
    """Clear the log buffer."""
    try:
        shared_log_buffer.clear()
        logger.info("Log buffer cleared")
        return {"message": "Log buffer cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear logs: {str(e)}")
        return {"error": str(e)}


@router.get("/api/logs/stream")
async def stream_logs():
    """Stream log buffer updates using Server-Sent Events."""

    async def event_generator():
        last_count = 0
        last_version = shared_log_buffer.get_version()  # Track version to detect clears

        # Send initial logs
        try:
            current_logs = shared_log_buffer.get_logs()
            if current_logs:
                for log in current_logs:
                    yield f"data: {json.dumps({'log': log})}\n\n"
                last_count = len(current_logs)
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get initial logs: {str(e)}'})}\n\n"

        # Stream new logs
        while True:
            try:
                await asyncio.sleep(0.5)

                current_version = shared_log_buffer.get_version()
                current_logs = shared_log_buffer.get_logs()
                current_count = len(current_logs)

                # If buffer was cleared, reset counters
                if current_version != last_version:
                    last_version = current_version
                    last_count = 0

                # Send new logs
                if current_count > last_count:
                    new_logs = current_logs[last_count:]
                    for log in new_logs:
                        yield f"data: {json.dumps({'log': log})}\n\n"
                    last_count = current_count

            except Exception as e:
                yield f"data: {json.dumps({'error': f'Stream error: {str(e)}'})}\n\n"
                await asyncio.sleep(1)  # Slow down on error

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )