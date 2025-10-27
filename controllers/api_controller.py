# controllers/api_controller.py
import importlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import logging

app = FastAPI()
logger = logging.getLogger("api_controller")

class TriggerCmd(BaseModel):
    attack_type: str
    params: dict = {}

def start_api_server(command_queue, host="0.0.0.0", port=8000):
    """
    Run this in a background thread. It uses global command_queue to put commands.
    """
    # store queue in module-global for endpoints
    global CMD_Q
    CMD_Q = command_queue

    def run():
        # import uvicorn at runtime to avoid requiring the package at module import time
        uvicorn = importlib.import_module("uvicorn")
        uvicorn.run(app, host=host, port=port, log_level="info")
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread

@app.post("/trigger")
def trigger_attack(cmd: TriggerCmd):
    if 'CMD_Q' not in globals():
        raise HTTPException(status_code=500, detail="Command queue not initialized")
    # enqueue command
    CMD_Q.put(("trigger_attack", {"attack_type": cmd.attack_type, "params": cmd.params}))
    logger.info(f"Enqueued attack trigger: {cmd.attack_type}")
    return {"status": "queued", "attack_type": cmd.attack_type}
