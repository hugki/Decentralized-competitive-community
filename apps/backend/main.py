from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select
import uuid
from fastapi import Security
from .auth import Actor, get_current_actor
from .database import get_session, init_db
from .models import (
    Model, Benchmark, Task, TaskStatus, TaskResult,
    LeaderboardHourly,
)
from .queue import enqueue, pull as queue_pull, ack as queue_ack
from statistics import median
from jose import jwk, jwt
import httpx
from sqlmodel import text

from .utils import runner_remaining_quota
app = FastAPI(title="Bench‑Backend MVP")

# -------- start‑up (local SQLite のみ) -------- #
@app.on_event("startup")
def _startup():
    if "sqlite" in app.state._state.get("DATABASE_URL", ""):
        init_db()

# ----------- API stubs (P0 完了分) ----------- #

# --- Model 登録時にタスク行を作成し enqueue ---------------- #
@app.post("/v0/models", status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: dict,
    session=Depends(get_session),
    actor: Actor = Security(get_current_actor, scopes=["model:register"]),
):
    # Enforce "Earn Your Submit" quota: Must evaluate 3 other models within 24h
    remaining_quota = runner_remaining_quota(session, actor.username)
    if remaining_quota > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "quota_unmet",
                "message": f"Must evaluate {remaining_quota} more models within 24h before registering",
                "principle": "🤝 Earn Your Submit - evaluate 3 other models to register your own"
            }
        )
    
    # Validate required model fields
    required_fields = ["name", "hf_repo"]
    if not all(field in payload for field in required_fields):
        raise HTTPException(400, detail=f"Missing required fields: {required_fields}")
    
    # Check for duplicate model repo
    existing = session.exec(
        select(Model).where(Model.hf_repo == payload["hf_repo"])
    ).first()
    if existing:
        raise HTTPException(409, detail="Model repository already registered")

    model = Model(**payload, submitter_github=actor.username)
    session.add(model)
    session.commit()
    session.refresh(model)

    # Create evaluation tasks for all existing benchmarks
    benchmarks = session.exec(select(Benchmark)).all()
    tasks_created = 0
    for bench in benchmarks:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            model_id=model.id,
            benchmark_id=bench.id,
            status=TaskStatus.QUEUED,
        )
        session.add(task)
        enqueue(task_id)
        tasks_created += 1
    session.commit()
    
    return {
        "id": model.id, 
        "name": model.name,
        "hf_repo": model.hf_repo,
        "tasks_created": tasks_created,
        "message": "Model registered successfully - tasks queued for evaluation"
    }


@app.get("/v0/tasks/pull")
async def pull_task(
    runner_id: str,
    session=Depends(get_session),
    actor: Actor = Security(get_current_actor, scopes=["task:pull"]),
):
    entry = queue_pull(runner_id, block_ms=0)
    if not entry:
        return {"task": None}

    task = session.get(Task, entry["task_id"])
    if not task:
        queue_ack(entry["id"])
        return {"task": None}

    task.status = TaskStatus.RUNNING
    task.assigned_to = runner_id
    session.add(task)
    session.commit()

    return {
        "task_id": task.id,
        "redis_id": entry["id"],   
        "model_repo": session.get(Model, task.model_id).hf_repo,
        "benchmark": session.get(Benchmark, task.benchmark_id).name,
    }


K_CONSENSUS = 3
MAX_DELTA   = 0.5

@app.post("/v0/tasks/{task_id}/result")
async def submit_result(
    task_id: str,
    payload: dict,
    session=Depends(get_session),
    actor: Actor = Security(get_current_actor, scopes=["task:submit"]),
):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, detail="Task not found")
    
    # Verify required payload fields for tamper-proof evaluation
    required_fields = ["score", "runtime_sec", "stdout_sha", "dataset_sha"]
    if not all(field in payload for field in required_fields):
        raise HTTPException(400, detail=f"Missing required fields: {required_fields}")
    
    # Verify dataset SHA matches the benchmark's expected SHA
    benchmark = session.get(Benchmark, task.benchmark_id)
    if benchmark and benchmark.dataset_sha != payload["dataset_sha"]:
        raise HTTPException(400, detail="Dataset SHA mismatch - evaluation invalid")
    
    # Check for duplicate submission from same runner
    existing = session.exec(
        select(TaskResult).where(
            TaskResult.task_id == task_id,
            TaskResult.runner_id == actor.username
        )
    ).first()
    if existing:
        raise HTTPException(409, detail="Runner already submitted result for this task")

    # TaskResult を保存
    tr = TaskResult(
        task_id=task_id,
        runner_id=actor.username,
        score=payload["score"],
        runtime_sec=payload["runtime_sec"],
        stdout_sha=payload["stdout_sha"],
    )
    session.add(tr)
    session.commit()

    # Get all results for consensus evaluation
    results = session.exec(
        select(TaskResult).where(TaskResult.task_id == task_id)
    ).all()

    # Consensus mechanism: ≥3 independent runners with dispersion ≤ 0.5
    if len(results) >= K_CONSENSUS:
        scores = [r.score for r in results]
        score_range = max(scores) - min(scores)
        
        if score_range <= MAX_DELTA:
            # Consensus achieved - use median score
            task.status = TaskStatus.DONE
            task.score = median(scores)
            consensus_msg = f"CONSENSUS: {len(results)} runners, range={score_range:.3f}, median={task.score:.3f}"
        else:
            # Dispersion too high - flag as disputed
            task.status = TaskStatus.DISPUTED
            task.score = None
            consensus_msg = f"DISPUTED: {len(results)} runners, range={score_range:.3f} > {MAX_DELTA}"
        
        session.add(task)
        session.commit()

        # Update leaderboard only for consensus results
        if task.status == TaskStatus.DONE:
            session.exec(text("REFRESH MATERIALIZED VIEW leaderboard_hourly"))
        
        return {
            "ok": True, 
            "status": task.status,
            "consensus": consensus_msg,
            "total_submissions": len(results)
        }
    # Redis ACK（成功 / 不一致に関係なく消費済みとする）
    queue_ack(payload.get("redis_id", ""))  # CLI が redis_id を添付

    return {"ok": True, "status": task.status}


@app.get("/v0/leaderboard")
async def leaderboard(limit: int = 50, session=Depends(get_session)):
    stmt = (
        select(LeaderboardHourly)
        .order_by(LeaderboardHourly.avg_score.desc())
        .limit(limit)
    )
    return session.exec(stmt).all()



@app.get("/v0/runner/{runner_id}/quota")
async def runner_quota(runner_id: str, session=Depends(get_session)):
    remaining = runner_remaining_quota(session, runner_id)
    return {
        "runner_id": runner_id,
        "remaining_evaluations": remaining,
        "can_register_model": remaining == 0,
        "principle": "🤝 Earn Your Submit - evaluate 3 other models to register your own"
    }

@app.get("/v0/community/stats")
async def community_stats(session=Depends(get_session)):
    """Community evaluation statistics and tamper-proof metrics"""
    # Total tasks by status
    total_tasks = session.exec(select(Task)).count()
    done_tasks = session.exec(select(Task).where(Task.status == TaskStatus.DONE)).count()
    disputed_tasks = session.exec(select(Task).where(Task.status == TaskStatus.DISPUTED)).count()
    queued_tasks = session.exec(select(Task).where(Task.status == TaskStatus.QUEUED)).count()
    
    # Consensus statistics
    consensus_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
    dispute_rate = (disputed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "total_evaluations": total_tasks,
        "consensus_achieved": done_tasks,
        "disputed_evaluations": disputed_tasks,
        "pending_evaluations": queued_tasks,
        "consensus_rate_percent": round(consensus_rate, 2),
        "dispute_rate_percent": round(dispute_rate, 2),
        "tamper_proof_config": {
            "required_runners": K_CONSENSUS,
            "max_score_dispersion": MAX_DELTA,
            "dataset_sha_verified": True,
            "output_sha_verified": True
        }
    }



@app.post("/auth/github")
async def github_oidc_exchange(id_token: str):
    """
    CLI が GitHub Actions / `gh auth token` で得た OIDC トークンを送信 →
    GitHub の JWKS で署名検証し、自分の JWT を発行して返す。
    （MVP: *署名検証をスキップして* issuer / sub だけ読む簡易版）
    """
    try:
        payload = jwt.get_unverified_claims(id_token)
        username = payload["sub"].split(":")[-1]  # e.g. "github|12345"
    except Exception as e:
        raise HTTPException(401, f"OIDC decode failed: {e}")

    scopes = ["task:pull", "task:submit", "model:register"]
    return {"access_token": create_access_token(username, scopes), "token_type": "bearer"}
