import json, asyncio, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis import redis_client
from app.core.security import decode_token

logger = logging.getLogger("bgbot.ws")
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    await websocket.accept()
    if not token:
        try:
            first = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            msg = json.loads(first)
            token = msg.get("token")
        except Exception:
            await websocket.close(code=4001)
            return
    if not token:
        await websocket.close(code=4001)
        return
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    user_id = payload.get("uid")
    if not user_id:
        await websocket.close(code=4001)
        return
    logger.info(f"WS connected: user {user_id}")
    channel = f"user:{user_id}:events"
    ps = redis_client.pubsub()
    await ps.subscribe(channel)

    async def listen_redis():
        try:
            async for message in ps.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes): data = data.decode()
                    await websocket.send_text(data)
        except Exception: pass

    task = asyncio.create_task(listen_redis())
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            event = msg.get("event")
            event_data = msg.get("data", {})
            if event == "get_state":
                await redis_client.publish(f"user:{user_id}:control", json.dumps({"action": "get_state"}))
            elif event == "start_bot":
                await redis_client.publish(f"user:{user_id}:control", json.dumps({"action": "start"}))
            elif event == "stop_bot":
                await redis_client.publish(f"user:{user_id}:control", json.dumps({"action": "stop"}))
            elif event == "save_config":
                await redis_client.publish(f"user:{user_id}:config", json.dumps(event_data))
    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {user_id}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        task.cancel()
        await ps.unsubscribe(channel)
        await ps.close()
