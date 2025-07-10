import json, os, pathlib, typer, uuid, requests
from rich import print
import subprocess, tempfile, shutil, uuid

HF_CACHE = pathlib.Path.home() / ".cache" / "huggingface"

API = os.getenv("BENCH_API_URL", "http://localhost:8000")
CONFIG_PATH = pathlib.Path.home() / ".bench" / "config.json"
app = typer.Typer()

def save_config(data: dict):
    CONFIG_PATH.parent.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data))

def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    typer.echo("not logged in. run `bench login`"); raise typer.Exit()

# ---------- login ---------- #
@app.command()
def login(gh_oidc_token: str = typer.Option(..., "--token")):
    """GitHub OIDC トークンを JWT に交換し保存"""
    r = requests.post(f"{API}/auth/github", json={"id_token": gh_oidc_token})
    r.raise_for_status()
    data = r.json()
    save_config(data)
    print("[green]login success[/green]")

# ---------- pull ---------- #
@app.command()
def pull(
    runner_id: str = typer.Option(...),
    auto: bool = typer.Option(False, help="取得後すぐ実行・submit"),
):
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['access_token']}"}

    r = requests.get(f"{API}/v0/tasks/pull", params={"runner_id": runner_id}, headers=headers)
    r.raise_for_status()
    task = r.json()
    if task.get("task_id") is None:
        print("no task"); return

    if not auto:
        typer.echo("saved current_task.json")
        pathlib.Path("current_task.json").write_text(json.dumps(task))
        return

    work = pathlib.Path(tempfile.mkdtemp())
    try:
        run_task(task, work, cfg)
    finally:
        shutil.rmtree(work, ignore_errors=True)

def run_task(task: dict, work: pathlib.Path, cfg: dict):
    """Docker で run_eval.py を回し submit"""
    out_json = work / "out.json"
    docker_cmd = [
        "docker", "run", "--rm", "--gpus", "all",
        "-v", f"{HF_CACHE}:{'/root/.cache/huggingface'}",
        "-v", f"{work}:/workspace",
        "bench/runtime:0.1",
        "--model", task["model_repo"],
        "--benchmark", task["benchmark"],
        "--task-id", task["task_id"],
        "--output", "/workspace/out.json",
    ]
    typer.echo(" ".join(docker_cmd))
    subprocess.run(docker_cmd, check=True)

    # submit
    payload = json.loads(out_json.read_text())
    payload["redis_id"] = task["redis_id"]       # ACK 用
    headers = {"Authorization": f"Bearer {cfg['access_token']}"}
    r = requests.post(
        f"{API}/v0/tasks/{task['task_id']}/result",
        json=payload,
        headers=headers,
    )
    r.raise_for_status()
    print("[green]submitted[/green]", r.json())

@app.command()
def run(task_json: pathlib.Path, out: pathlib.Path = pathlib.Path("out.json")):
    """開発用：ローカルでモデル/ベンチ名を指定して評価 → out.json"""
    task = json.loads(task_json.read_text())
    run_task(task, pathlib.Path("."), load_config())

# ---------- submit ---------- #
@app.command()
def submit(result_json: pathlib.Path):
    cfg = load_config()
    headers = {"Authorization": f"Bearer {cfg['access_token']}"}
    payload = json.loads(result_json.read_text())
    r = requests.post(f"{API}/v0/tasks/{payload['task_id']}/result", json=payload, headers=headers)
    r.raise_for_status()
    print(r.json())
