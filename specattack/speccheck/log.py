"""JSON-lines logs. One file per experiment (logs/<experiment>.jsonl); a rerun
moves the previous file to logs/archive/ first, so a log always describes one
complete run."""

import json
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import z3

from . import config


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else "no-git"
    except (OSError, subprocess.SubprocessError):
        return "no-git"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RunLogger:
    def __init__(self, results_dir, experiment, settings=None):
        self.logs = Path(results_dir) / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.experiment = experiment
        self.run_id = f"{experiment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.commit = git_commit()
        self.path = self.logs / f"{experiment}.jsonl"
        if self.path.exists():
            archive = self.logs / "archive"
            archive.mkdir(exist_ok=True)
            stamp = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            self.path.replace(archive / f"{experiment}-{stamp}.jsonl")
        meta = {
            "run_id": self.run_id,
            "experiment": experiment,
            "timestamp": now(),
            "git_commit": self.commit,
            "z3_version": z3.get_version_string(),
            "python_version": platform.python_version(),
            "N": config.N,
            "z3_timeout_ms": config.Z3_TIMEOUT_MS,
            "writer_model": config.WRITER_MODEL,
            "writer_thinking_effort": config.WRITER_THINKING_EFFORT,
            "attacker_model": config.ATTACKER_MODEL,
            "attacker_thinking_effort": config.ATTACKER_THINKING_EFFORT,
        }
        meta.update(settings or {})
        with open(self.logs / "run_meta.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(meta) + "\n")

    def write(self, record_type, record):
        line = {"record_type": record_type, "run_id": self.run_id, "timestamp": now(),
                "git_commit": self.commit, **record}
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, default=str) + "\n")


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
