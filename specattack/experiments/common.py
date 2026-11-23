"""Shared command-line options, LLM clients and helpers for the experiment scripts."""

import argparse
import sys
import time
from pathlib import Path

import benchmarks
from speccheck import config
from speccheck.llm import LLMClient, has_credentials, role_effort


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--results-dir", default=str(config.DEFAULT_RESULTS_DIR),
                   help="where logs, cache, tables and figures go (default: results/)")
    p.add_argument("--tasks", nargs="*", help="run only these task ids")
    p.add_argument("--fresh", action="store_true",
                   help="ask the LLM again for every call and overwrite the saved replies (default: reuse the "
                        "replies saved in results/cache/, so only calls not made before cost anything)")
    return p


def tasks(args):
    return benchmarks.select(args.tasks)


def clients(args):
    """(writer, attacker) LLM clients. Stops with a short message if the API key is missing."""
    return (_client(args, config.WRITER_MODEL, role_effort("writer")),
            _client(args, config.ATTACKER_MODEL, role_effort("attacker")))


def writer_client(args, model, effort):
    """A spec writer with another model or effort (Exp 3)."""
    return _client(args, model, effort)


def _client(args, model, effort):
    if not has_credentials():
        sys.exit('No API credentials. Set your Anthropic API key first, for example '
                 '$env:ANTHROPIC_API_KEY = "sk-ant-..." (see README).')
    return LLMClient(model, Path(args.results_dir) / "cache", effort=effort, replay=not args.fresh)


def first_spec_id(task_id, repeat):
    return f"{task_id}-r{repeat}"


class NullLogger:
    """Drop-in logger that keeps records in memory (tests)."""

    def __init__(self):
        self.records = []

    def write(self, record_type, record):
        self.records.append((record_type, record))


class Progress:
    """One line per item with a counter in front, as "[ 12/50]  24% ...", and the duration at the end."""

    def __init__(self, title, total):
        self.title, self.total, self.done = title, total, 0
        self.started = time.perf_counter()

    def item(self, text):
        self.done += 1
        percent = 100 * self.done // self.total if self.total else 100
        print(f"[{self.done:>{len(str(self.total))}}/{self.total}] {percent:3d}% {text}", flush=True)

    def finish(self):
        print(f"{self.title}: done in {format_duration(time.perf_counter() - self.started)}", flush=True)


def format_duration(seconds):
    minutes, seconds = divmod(round(seconds), 60)
    return f"{minutes} min {seconds} s" if minutes else f"{seconds} s"
