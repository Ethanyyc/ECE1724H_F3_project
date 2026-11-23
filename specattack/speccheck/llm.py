"""LLM access with a response cache and cost accounting.

The cache key is a hash of (model, prompt, settings, call tag). The tag names
the call (for example "exp1:pivot_index:r0" or "exp2:pivot_index-r0:t3:k2"), so
every call is a separate sample. Every reply is saved; a client with
replay=True answers from the saved replies when it can (a rerun then costs
nothing), while replay=False always asks the LLM and overwrites the saved
reply. A replayed result keeps the token counts, cost and latency of the
original call, so RQ4 measures real calls.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Callable, Optional

from . import config

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
_UNPRICED_WARNED = set()


@dataclass
class LLMResult:
    text: str
    model: str                       # model requested
    model_version: str               # model reported by the API
    tokens_in: int
    tokens_out: int                  # billed output tokens, including thinking
    tokens_thinking: Optional[int]   # reported thinking tokens (None if the API does not report them)
    cost_usd: float
    latency_ms: float
    stop_reason: str
    thinking: str                    # e.g. "adaptive/low"
    cache_hit: bool = False
    cache_key: Optional[str] = None  # file name of the saved reply in results/cache/


def has_credentials():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def make_anthropic_client():
    """An Anthropic SDK client; the SDK reads the key from ANTHROPIC_API_KEY."""
    import anthropic   # imported lazily so that the tests do not need the SDK set up
    return anthropic.Anthropic(timeout=config.LLM_TIMEOUT_S, max_retries=config.LLM_MAX_RETRIES)


def role_effort(role):
    """Adaptive-thinking effort of the "writer" or the "attacker"."""
    return {"writer": config.WRITER_THINKING_EFFORT, "attacker": config.ATTACKER_THINKING_EFFORT}[role]


def cost_of(model, tokens_in, tokens_out):
    """USD cost of one call, from config.PRICES_PER_MTOK."""
    prices = config.PRICES_PER_MTOK.get(model)
    if prices is None:
        if model not in _UNPRICED_WARNED:
            _UNPRICED_WARNED.add(model)
            print(f"WARNING: no price for model {model} in config.PRICES_PER_MTOK; its cost is recorded as $0")
        return 0.0
    return round((tokens_in * prices["input"] + tokens_out * prices["output"]) / 1e6, 6)


class ResponseCache:
    def __init__(self, directory):
        self.directory = Path(directory)

    def key(self, material):
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()

    def _path(self, key):
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key):
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))["result"]

    def put(self, key, material, result):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"material": material, "result": result}, indent=1), encoding="utf-8")
        tmp.replace(path)


class LLMClient:
    """Anthropic Messages API with adaptive thinking at a fixed effort."""

    def __init__(self, model, cache_dir, effort, replay=True):
        if effort not in EFFORT_LEVELS:
            raise ValueError(f"unknown thinking effort {effort!r} for {model}")
        self.model, self.effort, self.replay = model, effort, replay
        self.cache = ResponseCache(cache_dir)
        self._client = None

    def thinking_label(self):
        return f"adaptive/{self.effort}"

    def complete(self, prompt, tag):
        material = {"model": self.model, "prompt": prompt, "max_tokens": config.MAX_TOKENS,
                    "thinking": self.thinking_label(), "tag": tag}
        key = self.cache.key(material)
        cached = self.cache.get(key) if self.replay else None
        if cached is not None:
            known = {field.name for field in fields(LLMResult)}
            return LLMResult(**{**{k: v for k, v in cached.items() if k in known}, "cache_hit": True, "cache_key": key})
        result = self._call(prompt)
        result.cache_key = key
        self.cache.put(key, material, asdict(result))
        return result

    def _request(self, prompt):
        return {"model": self.model, "max_tokens": config.MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
                "thinking": {"type": "adaptive"}, "output_config": {"effort": self.effort}}

    def _call(self, prompt):
        if self._client is None:
            self._client = make_anthropic_client()
        start = time.perf_counter()
        response = self._client.messages.create(**self._request(prompt))
        latency = (time.perf_counter() - start) * 1000
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        usage = response.usage
        details = getattr(usage, "output_tokens_details", None)
        return LLMResult(
            text=text, model=self.model, model_version=getattr(response, "model", self.model),
            tokens_in=usage.input_tokens, tokens_out=usage.output_tokens,
            tokens_thinking=getattr(details, "thinking_tokens", None) if details is not None else None,
            cost_usd=cost_of(self.model, usage.input_tokens, usage.output_tokens),
            latency_ms=round(latency, 1), stop_reason=str(getattr(response, "stop_reason", "")),
            thinking=self.thinking_label(),
        )


class FakeLLM:
    """Scripted replies for the unit tests. responder(prompt, tag) returns the reply
    text; token counts are rough estimates, priced like the writer model."""

    model = "fake"

    def __init__(self, responder: Callable[[str, str], str]):
        self.responder = responder
        self.calls = []

    def complete(self, prompt, tag):
        text = self.responder(prompt, tag)
        self.calls.append((tag, prompt, text))
        tokens_in, tokens_out = len(prompt) // 4, len(text) // 4 + 50
        return LLMResult(text=text, model="fake", model_version="fake", tokens_in=tokens_in, tokens_out=tokens_out,
                         tokens_thinking=50, cost_usd=cost_of(config.WRITER_MODEL, tokens_in, tokens_out), latency_ms=0.0,
                         stop_reason="end_turn", thinking="fake")
