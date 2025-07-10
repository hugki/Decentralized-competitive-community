"""
Redis Streams helper
────────────────────
Stream   :  tasks
Fields   :  task_id=<uuid>
Group    :  runners
Consumer :  <runner_id>
"""
from __future__ import annotations

import os
from datetime import timedelta, datetime
from redis import Redis
from redis.exceptions import ResponseError

STREAM = "tasks"
GROUP = "runners"
MAX_IDLE = timedelta(minutes=30)      # 30 min で再配布

redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def _init_group() -> None:
    """Idempotent ― 無ければ consumer‑group を作る"""
    try:
        redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            return
        raise


def enqueue(task_id: str) -> None:
    _init_group()
    redis.xadd(STREAM, {"task_id": task_id})


def pull(runner_id: str, block_ms: int = 0) -> dict | None:
    """
    return {"id": redis_id, "task_id": "..."} または None
    """
    _init_group()
    res = redis.xreadgroup(
        GROUP,
        runner_id,
        streams={STREAM: ">"},
        block=block_ms,
        count=1,
    )
    if not res:
        # idle > MAX_IDLE の保留メッセージを claim
        pending = redis.xpending_range(
            STREAM, GROUP, min="-", max="+", count=1, consumer=None, idle=MAX_IDLE
        )
        if pending:
            entry = pending[0]
            redis_id = entry["message_id"]
            redis.xclaim(STREAM, GROUP, runner_id, min_idle_time=MAX_IDLE, message_ids=[redis_id])
            task_id = redis.xrange(STREAM, min=redis_id, max=redis_id)[0][1][b"task_id"].decode()
            return {"id": redis_id, "task_id": task_id}
        return None

    redis_id, fields = res[0][1][0]
    task_id = fields[b"task_id"].decode()
    return {"id": redis_id.decode(), "task_id": task_id}


def ack(redis_id: str) -> None:
    redis.xack(STREAM, GROUP, redis_id)
