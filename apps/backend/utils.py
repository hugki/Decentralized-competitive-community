from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from .models import TaskResult, Model

NORM_REQUIRED = 3
WINDOW = timedelta(hours=24)

def runner_remaining_quota(session: Session, username: str) -> int:
    """
    戻り値: 残りノルマ数 (0 なら OK)
    """
    since = datetime.now(timezone.utc) - WINDOW

    # 自分のモデル ID
    own_model_ids = {
        m.id
        for m in session.exec(
            select(Model.id).where(Model.submitter_github == username)
        )
    }

    # 他者モデルを評価した TaskResult 数
    cnt = session.exec(
        select(TaskResult)
        .where(
            TaskResult.runner_id == username,
            TaskResult.created_at > since,
            TaskResult.task_id.not_in(own_model_ids)
            if own_model_ids
            else True,
        )
    ).count()

    remaining = max(0, NORM_REQUIRED - cnt)
    return remaining
