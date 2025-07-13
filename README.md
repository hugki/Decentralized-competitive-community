## What & Why

**Decentralized-competitive-community** is a community-run, *zero-storage* leaderboard for open-source LLM and LoRA checkpoints on Hugging Face Hub.  
The guiding principles are:

| Principle | Rationale & Implementation |
|-----------|----------------------------|
| **🌐 Radical Piggy-backing** | All heavy assets (models, branches, logs) live on *external* platforms—mostly HF Hub & GitHub. Our DB only stores immutable URLs + numeric scores, keeping infra bills and lock-in near zero. |
| **🔬 Micro-benchmarks, Hourly** | We evaluate *5 shots* of **TruthfulQA** and **GSM8K** every hour. It’s tiny enough for hobby GPUs yet fresh enough to track rapid LoRA iterations. |
| **🔒 Tamper-proof by Design** | Each run is anonymously cross-checked by ≥ 3 independent runners. Median wins if dispersion ≤ 0.5; else the task is flagged **DISPUTED**. Datasets are pinned by git-SHA, outputs are SHA-256’d. |
| **🤝 Earn Your Submit** | To register a model you must first evaluate *three* other models within 24 h—ensuring the queue is always moving without a central compute budget. |
| **♻️ Extensible Scoring** | Schema is generic (`Task ↔ Benchmark ↔ Result`). Future axes—human star-ratings, Green Score (kWh/CO₂), adversarial robustness—drop in as extra columns & materialized-view math. |
| **🪤 Minimal Surfacing** | The website does exactly two things: accept signed results & sort them. Everything else—model hosting, branch history, rich demo cards—stays on the services that already excel at it. |

### Current MVP Snapshot

* **Backend** : FastAPI + PostgreSQL(+Timescale) + Redis Streams, auto-deployed to Fly.io  
* **Runner** : Typer CLI → Docker runtime (multi-arch), pushes results to API  
* **Benchmarks** : TruthfulQA (5) & GSM8K (5) on HF Datasets  
* **Leaderboard UI** : Next.js 14 (app router) on Vercel, SWR polls every 60 s  
* **CI/CD** : GitHub Actions – pytest + ruff; runtime image to GHCR; backend rolling-deploy

The architecture is intentionally sparse so that future features—larger tasks, qualitative reviews, eco-metrics, contributor-driven new benchmarks—slot in with additive migrations and new JWT scopes, *not* rewrites.

> **Mission statement:** *Democratize rapid, accountable, environment-aware evaluation of small-scale LLM tweaks—without re-inventing model hosting or shouldering petabyte bills.*


## 0. TL;DR for Agents 🤖

1. **Clone** → **`make dev`** → services come up locally.
2. **Pick an Issue** in `docs/ISSUES.md` or open a new one.
3. `git checkout -b feat/<topic>` → code → `pytest -q && ruff .` → `gh pr create`.
4. CI will: lint + unit-test → build runtime image (`ghcr.io/...`) → deploy Backend to Fly → Vercel preview.

Everything else you need (architecture, env-vars, extension hooks, coding conventions) is documented below so an autonomous agent can proceed end-to-end with **zero human context-switch**.

---

## 1. Vision & Non-Goals

|                            |                                                                                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mission**                | Hourly, tamper-proof micro-benchmarks for **HF Hub LLM / LoRA** models that give public credit to contributors.                                                                             |
| **Zero-Storage Principle** | **Binary weights / branches / logs are *never* stored here.** We only keep:<br> • model URL (optionally `org/repo@sha`)<br> • numeric scores & metadata<br> • contributor account + credits |
| **MVP Benchmarks**         | TruthfulQA (5 samples) & GSM8K (5 samples)                                                                                                                                                  |
| **Update cadence**         | Leaderboard refresh on every finished task ( ≤ 1 h latency )                                                                                                                                |
| **α-phase Exclusions**     | Secure enclaves / ZK proofs, multilingual benchmarks, pretty UI                                                                                                                             |

---

## 2. High-Level System Diagram

```
bench-cli (runner)  <--Redis Streams-->  Backend API (FastAPI)
    |                                           |
    |  Docker eval                               |  PostgreSQL(+Timescale)  <-- materialized view
    |                                           |
 Next.js UI  <-- REST/JSON -->  Backend API  <-- task consensus + cron
```

---

## 3. Current Repository Layout

```
repo/
├─ apps/
│  ├─ backend/         # FastAPI + SQLModel + Redis Streams
│  ├─ bench-cli/       # Typer CLI & Docker runtime
│  └─ frontend/        # Next.js 14 (app router)
├─ alembic/            # DB migrations
├─ .github/workflows/  # CI / CD (runtime build, Fly deploy)
├─ charts/             # (placeholder) helm manifests
└─ infra/terraform/    # (placeholder) staging IaC
```

<details>
<summary>File-level tree</summary>

```
apps/backend/
  ├─ auth.py            # JWT scopes, GitHub OIDC exchange
  ├─ config.py
  ├─ database.py
  ├─ main.py            # 5 core endpoints + consensus logic
  ├─ models.py          # SQLModel ORM
  ├─ queue.py           # Redis Streams helper
  ├─ utils.py           # quota calc etc.
  ├─ Dockerfile
  └─ fly.toml

apps/bench-cli/
  ├─ main.py            # login / pull / run / submit
  └─ runtime/
      ├─ Dockerfile     # multi-arch CPU runtime image
      └─ run_eval.py    # TruthfulQA & GSM8K scorer

apps/frontend/
  ├─ app/               # Next.js pages
  └─ lib/fetcher.ts
```

</details>

---

## 4. Local Development

```bash
# dependencies: docker, python3.11, node18, pnpm (or npm/yarn), uv

# Quick setup with uv (fastest)
make dev             # installs uv, syncs dependencies, sets up environment
source env/dev.sh    # exports environment variables
make migrate         # run database migrations
make run-backend     # start backend server (http://localhost:8000)

# In another terminal
make run-frontend    # start frontend (http://localhost:3000/leaderboard)

# Traditional setup (slower)
uv sync
source env/dev.sh
uv run alembic upgrade head
uv run uvicorn apps.backend.main:app --reload

# Build runtime image
docker build -t bench/runtime:0.1 apps/bench-cli/runtime

# CLI usage (with dummy token for local dev)
export BENCH_API_URL=http://localhost:8000
uv run bench login --token dummy
uv run bench pull --runner-id mygpu --auto
```

### Development Commands

- `make dev` - Setup development environment with uv
- `make run-backend` - Start FastAPI backend server
- `make run-frontend` - Start Next.js frontend
- `make migrate` - Run database migrations
- `make test` - Run test suite
- `make lint` - Run linting and type checking

The project now uses **uv** for blazing-fast Python package management and development.

---

## 5. Runtime & Scoring

* **Data**: sub-sampling of HF Datasets deterministically by SHA.
* **`run_eval.py`** loads model → runs 5 prompts → returns `mean_score`, `runtime_sec`, `stdout_sha`.
* **Energy / CO₂** can be added later by self-reporting `--gpu-type` & power draw; DB already stores runtime seconds.

---

## 6. Consensus & Security

| Layer        | Mechanism                                                        |
| ------------ | ---------------------------------------------------------------- |
| Tamper proof | `dataset_sha`, `stdout_sha`, median of ≥3 runs (`max-min < 0.5`) |
| Quorum       | `K_CONSENSUS = 3`, else `DISPUTED` + re-queue                    |
| Isolation    | Docker with `--network none --pids-limit 512`                    |
| AuthN/Z      | GitHub OIDC → JWT `scope` (task\:pull/submit, model\:register)   |
| Quota        | `NORM_REQUIRED = 3` tasks/24 h per submitter                     |

---

## 7. CI / CD

| Workflow               | Trigger                                          | Result                                                                |
| ---------------------- | ------------------------------------------------ | --------------------------------------------------------------------- |
| **docker-runtime.yml** | push to `main`, path `apps/bench-cli/runtime/**` | Build **multi-arch** image → push `ghcr.io/<org>/bench-runtime:<tag>` |
| **fly-deploy.yml**     | push to `main`, path `apps/backend/**`           | `flyctl deploy` backend                                               |
| **ci.yml**             | any push / PR                                    | `pytest + ruff + mypy`                                                |

Secrets needed in repo: `FLY_API_TOKEN`. Fly app secrets: `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`.

---

## 8. Extensibility Roadmap

| Roadmap item                   | One-liner How-To                                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Human/Qualitative tasks**    | add `benchmark.type='human'`, route to external label UI, store 1-5★ in `TaskResult.score`.          |
| **Green score (energy / CO₂)** | extend `TaskResult` with `energy_kwh`; compute `green_score = f(acc, co₂)` in MV.                    |
| **Dynamic quota / window**     | env `NORM_REQUIRED`, `NORM_WINDOW_H`; expose `/admin/settings`.                                      |
| **User role escalation**       | materialized view `contributor_level`; cron grants JWT scope `benchmark:create` when thresholds met. |
| **New benchmarks**             | `POST /v0/benchmarks` (scope: `benchmark:create`) → enqueue same task matrix automatically.          |
| **External storage only**      | enforce `model.hf_repo` includes git SHA; keep **no blobs** locally.                                 |

The DB & API surface were intentionally generic so the above need **only column additions and ENV flips**, no rewrite.

---

## 9. Contributing Guidelines (for Humans & Agents)

* **Branch naming**: `feat/<topic>`, `fix/<bug>`, `docs/<area>`.
* **Commits**: conventional-commits (`feat:`, `fix:`, `refactor:` …).
* **Tests**: every PR must add/modify unit tests if logic changes.
* **Lint**: `ruff --fix .` before pushing.
* **PR checklist** (enforced by CI):

  1. Unit tests pass
  2. `ruff` & `mypy` clean
  3. No TODO/FIXME committed
  4. Updated docs / OpenAPI schema

---

## 10. Issue Backlog Snapshot (`docs/ISSUES.md`)

| Pri | Title                           | Area     | Brief                                      |
| --- | ------------------------------- | -------- | ------------------------------------------ |
| P0  | `perf/prefetch-dataset-cache`   | runtime  | warm HF dataset shards in image            |
| P1  | `feat/green-score-plumbing`     | backend  | add energy\_kwh column, ENV `WATT_PER_GPU` |
| P1  | `feat/benchmark-create-endpt`   | backend  | gated by `benchmark:create` scope          |
| P2  | `feat/human-review-portal`      | frontend | minimal crowd UI + Slack/webhook login     |
| P3  | `docs/architecture-diagram.svg` | docs     | nice diagram for README                    |

Agents may autonomously assign themselves (`/assign @agent-name`) and move cards on the GitHub Projects board.

---

### ☑️ MVP status: **COMPLETE**

The system runs end-to-end in prod-like conditions with hourly leaderboard, quota gating, CI/CD and no local model storage. Future items fit naturally via additive migrations and scope tweaks.

*This README is intentionally exhaustive so that an LLM-powered agent can onboard, pick issues, and continue development without extra context.*

READMEのロードマップセクションを、5ショット評価の拡張性について明確にする形で修正します：

```markdown

---

## 11. Long-term Roadmap: Towards Community-Driven Model Development

Our MVP intentionally starts minimal, but the vision extends far beyond simple benchmarking. We're building the foundation for a community where model evaluation and development are deeply intertwined.

### Phase 1: Foundation (Current MVP) ✅
- Basic leaderboard with TruthfulQA & GSM8K micro-benchmarks
- **5-shot evaluation as extensible baseline** (not a limitation, but a starting point)
- Tamper-proof consensus mechanism
- Contributor quota system
- Zero-storage architecture

### Phase 2: Scalable Evaluation Framework (Q2 2025)
- **Dynamic shot configuration**: 5 → 25 → 100+ shots based on task complexity
- **Adaptive evaluation depth**: More shots for close competitions, fewer for clear winners
- **Community-defined evaluation budgets**: Collectively decide compute allocation
- **Progressive evaluation**: Start with 5-shot, expand if model shows promise
- **Evaluation effort remains constant**: Whether quota is 3 or 10, total community workload stays balanced

#### Key Design Principle: Evaluation Elasticity
```yaml
evaluation_depth:
  quick_filter: 5 shots      # MVP: rapid iteration
  standard: 25 shots         # Default for established models
  comprehensive: 100+ shots  # For top-tier models
  custom: community_defined  # Task-specific requirements

# Total community compute remains constant:
# 1000 models × 5 shots = 200 models × 25 shots = 50 models × 100 shots

Phase 3: Evaluation Diversity & Model Repository Integration (Q3 2025)

Human-in-the-loop evaluation: Subjective quality assessments
Multi-modal benchmarks: Image, audio, video comprehension
Domain-specific tracks: Medical, Legal, Code, Scientific reasoning
Commit-level tracking: Link submissions to specific model commits
Training metadata: Attach configs, datasets, compute requirements
Lineage graphs: Visualize model family trees and LoRA inheritance

Phase 4: Community Governance (Q4 2025)

Evaluation DAO: Token-based voting on benchmark selection and shot counts
Contributor tiers:

Evaluators: Run benchmarks, earn credits
Benchmark Authors: Design tasks and define appropriate shot counts
Core Contributors: Define evaluation methodology and resource allocation


Dynamic quota system: Adjust based on current queue and evaluation depth
Compute pooling: Share resources for deeper evaluations of promising models

Phase 5: Evaluation-Driven Development (2026)

Auto-improvement loops: Models fine-tune based on comprehensive evaluation
Tiered evaluation pipeline:
New model → 5-shot screen → 25-shot validation → 100-shot certification

Community consensus on depth: Vote on how deeply to evaluate each model class
Best practices codification: Optimal shot counts for different model types
Impact-weighted evaluation: More shots for models with higher real-world usage

Technical Evolution for Scalable Evaluation
2025 Q1: Fixed 5-shot (MVP baseline)
2025 Q2: Configurable shots (5-100) + batched evaluation
2025 Q3: Adaptive depth based on score variance
2025 Q4: Community-voted evaluation budgets
2026:    ML-optimized shot selection
Evaluation Philosophy
The 5-shot baseline is not a compromise but a design choice for rapid iteration. The architecture supports:

Constant community workload: More models × fewer shots = Fewer models × more shots
Quality over quantity: Better to deeply evaluate important models than superficially evaluate all
Progressive refinement: Start fast, go deep when it matters
Community-driven depth: Let contributors decide where to invest evaluation effort

Getting Involved

Today: Run 5-shot evaluations, help establish baselines
Soon: Propose optimal shot counts for new benchmarks
Future: Vote on community evaluation budget allocation


"The best evaluation depth is not fixed—it emerges from community consensus and available resources."


## 🛠️ ローカル動作確認

以下は **Ubuntu/macOS, Apple Silicon・x86\_64 共通**。
Windows は WSL2 を推奨します。

### 0. 前提ツール

| ツール                     | Version (目安) | 用途                          |
| ----------------------- | ------------ | --------------------------- |
| Docker / Docker Desktop | 24+          | Postgres・Redis・runtime イメージ |
| Python                  | 3.11         | FastAPI backend / CLI       |
| Node.js                 | ≥ 18         | Next.js frontend            |
| pnpm \* or npm/yarn     | 最新           | package manager             |

\* **pnpm** を使う場合

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

---

### 1. リポジトリ取得

```bash
git clone https://github.com/<you>/llm-bench.git
cd llm-bench
```

---

### 2. インフラサービスを起動

#### 2-A. Docker Compose でまとめて

```bash
# 起動
docker compose -f dev-compose.yml up -d
# 構成:
#   postgres:5432  (user=postgres, pass=pass)
#   redis   :6379
```

<details>
<summary>dev-compose.yml 全文</summary>

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]

  redis:
    image: redis:7
    ports: ["6379:6379"]
```

</details>

#### 2-B. 直接 `docker run` 派の方

```bash
docker run -d --name pg -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16
docker run -d --name redis -p 6379:6379 redis:7
```

---

### 3. Python 仮想環境 & Backend

```bash
python -m venv .venv && source .venv/bin/activate
uv sync
```

#### 3-A. 環境変数

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:pass@localhost:5432/postgres"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="devsecret"               # 好きな文字列でOK
export BENCH_API_URL="http://localhost:8000"
```

`.env` を作る場合:

```
DATABASE_URL=postgresql+psycopg2://postgres:pass@localhost:5432/postgres
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=devsecret
```

#### 3-B. DB 初期化

```bash
alembic upgrade head                 # テーブル作成
```

サンプル・ベンチマークを投入 (TruthfulQA, GSM8K):

```bash
python - <<'PY'
from sqlmodel import SQLModel, Session, create_engine
from apps.backend.models import Benchmark
from apps.backend.config import Settings

import os
engine = create_engine(os.environ["DATABASE_URL"])
with Session(engine) as s:
    if not s.exec(SQLModel.select(Benchmark)).all():
        s.add_all([
            Benchmark(name="TruthfulQA", version="0.1", dataset_sha="sha-truth"),
            Benchmark(name="GSM8K",    version="0.1", dataset_sha="sha-gsm"),
        ])
        s.commit()
PY
```

#### 3-C. API 起動

```bash
uvicorn apps.backend.main:app --reload --port 8000
```

> OpenAPI が [http://localhost:8000/docs](http://localhost:8000/docs) で確認できます。

---

### 4. Runtime イメージをビルド (一度だけ)

```bash
docker build -t bench/runtime:0.1 apps/bench-cli/runtime
```

> Apple Silicon なら `--platform linux/arm64` を付けても OK。

---

### 5. CLI を使用

```bash
uv pip install --system -e apps/bench-cli        # Typer CLI を editable-install

# 「GitHub OIDC トークン」を省略する代わりに文字列 dummy を送る
bench login --token dummy
```

#### 5-A. タスクを引いて自動実行 & 提出

```bash
# GPU 名など一意な ID を runner-id に
watch -n60 'bench pull --runner-id mygpu --auto'
```

*pull → Docker で 5 問推論 → result JSON を backend に POST* がループします。
3 タスク終えたら **自身のモデル登録ノルマ** が満たされます。

#### 5-B. 手動で試す場合

```bash
bench pull --runner-id dev           # current_task.json が保存
bench run current_task.json          # 実行 (カレントで out.json 作成)
bench submit out.json                # 提出
```

---

### 6. フロントエンド

```bash
cd apps/frontend
pnpm i                               # npm i / yarn でも OK
pnpm dev                             # :3000 で起動
# http://localhost:3000/leaderboard が 60 s ごとにポーリング
```

> **環境変数**
> `NEXT_PUBLIC_API_URL` を `http://localhost:8000` にすると別ポート・別ホストでも動きます。
> ローカルは `.env.local` に書くだけで Next.js が拾います。

---

## 🎉 動作確認チェックリスト

1. `bench pull --auto` のログで

   * `docker run bench/runtime:0.1 ...` が成功
   * `submitted {'status': 'DONE'}` が返る
2. `uvicorn` 側のログに `POST /v0/tasks/<id>/result 200` が表示
3. `psql` で `SELECT * FROM leaderboard_hourly;` → `avg_score` が入っている
4. ブラウザ `localhost:3000/leaderboard` にモデルがランクイン

---

## トラブルシューティング

| 症状                               | 原因 / 解決                                                                    |
| -------------------------------- | -------------------------------------------------------------------------- |
| `bench pull` で **no task** と出続ける | ① モデルをまだ登録していない<br>② Redis が起動していない<br>→ `docker ps` で redis コンテナ確認        |
| `psycopg2.OperationalError`      | `DATABASE_URL` のパスワード・ポート誤り                                                |
| `CUDA out of memory`             | ランタイムを GPU 対応イメージに差し替え or `--gpus all` を外し CPU で試す                         |
| Leaderboard が更新されない              | materialized view が古い可能性 → `REFRESH MATERIALIZED VIEW leaderboard_hourly;` |

---