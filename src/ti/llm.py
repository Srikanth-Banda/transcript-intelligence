"""LLM client: OpenRouter through the OpenAI SDK, with a committed cache and a replay mode.

Why (DECISIONS.md D5, B2 criteria 1, 5, 6):
- every call is cached by a hash of stage, prompt version, prompt text, model slug, parameters and input, so
  a re-run never silently changes a result and evaluators can replay offline;
- TI_MODE=replay turns a cache miss into an error, never a network call;
- provider pinning (TI_PROVIDER_ORDER, no fallbacks) keeps one method across all calls;
- the key is read from the environment / .env and is never logged or written to the cache.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from . import CACHE_DIR, ROOT

T = TypeVar("T", bound=BaseModel)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_PARAMS = {"temperature": 0.0, "max_tokens": 4096}


class CacheMiss(RuntimeError):
    """Raised in replay mode when a result is not in the cache."""


class InvalidOutput(ValueError):
    """The model returned invalid JSON / schema output twice. Carries the last raw text and usage for evaluation."""

    def __init__(self, message: str, text: str = "", usage: dict | None = None, latency_s: float = 0.0):
        super().__init__(message)
        self.text = text
        self.usage = usage
        self.latency_s = latency_s


# ---- tracing hook (no-op by default; Langfuse is plugged in during the extras phase) ----------
class Tracer:
    @contextlib.contextmanager
    def span(self, name: str, **meta: Any) -> Iterator[dict]:
        yield {}

    def record(self, span: dict, **fields: Any) -> None:
        pass


NOOP_TRACER = Tracer()


def get_tracer() -> Tracer:
    if os.getenv("TI_TRACING", "0") == "1":
        raise NotImplementedError(
            "TI_TRACING=1 but no tracing plugin is installed. Langfuse support is added in the extras phase."
        )
    return NOOP_TRACER


# ---- cache -----------------------------------------------------------------------------------
def load_prompt(name: str) -> tuple[str, str]:
    """Return (version, prompt text) from prompts/<name>.md. Text is between the PROMPT START/END markers."""
    from . import PROMPT_DIR

    raw = (PROMPT_DIR / f"{name}.md").read_text()
    try:
        text = raw.split("<!-- PROMPT START -->", 1)[1].split("<!-- PROMPT END -->", 1)[0].strip()
    except IndexError:
        raise ValueError(f"prompts/{name}.md has no PROMPT START/END markers (stub prompt?)") from None
    return name, text


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cache_key(stage: str, prompt_version: str, prompt_sha: str, model: str, params: dict, input_hash: str) -> str:
    payload = json.dumps(
        {
            "stage": stage,
            "prompt_version": prompt_version,
            "prompt_sha": prompt_sha,
            "model": model,
            "params": params,
            "input": input_hash,
        },
        sort_keys=True,
    )
    return sha256(payload)


class LLMClient:
    def __init__(
        self,
        mode: str | None = None,
        cache_dir: Path | None = None,
        openai_client: Any = None,
        tracer: Tracer | None = None,
        min_interval: float | None = None,
        max_attempts: int = 5,
    ):
        load_dotenv(ROOT / ".env")  # key stays in the environment; never printed
        self.mode = (mode or os.getenv("TI_MODE", "live")).lower()
        if self.mode not in ("live", "replay"):
            raise ValueError("TI_MODE must be 'live' or 'replay'")
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self._client = openai_client
        self.tracer = tracer or get_tracer()
        self.min_interval = float(os.getenv("TI_MIN_INTERVAL", "0.2")) if min_interval is None else min_interval
        self.max_attempts = max_attempts
        self._last_call = 0.0

    # ---- public --------------------------------------------------------------------------
    def complete(
        self,
        *,
        stage: str,
        prompt_version: str,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        input_hash: str | None = None,
        params: dict | None = None,
    ) -> tuple[T, dict]:
        """Return (parsed output, meta). meta has cache_hit, model/provider returned, usage, key."""
        if not model:
            raise ValueError(f"no model slug set for {stage}; set TI_MODEL_{stage.upper()} in .env")
        params = {**DEFAULT_PARAMS, **(params or {})}
        provider_order = [p.strip() for p in os.getenv("TI_PROVIDER_ORDER", "").split(",") if p.strip()]
        if provider_order and "provider_order" not in params:
            params["provider_order"] = provider_order
        input_hash = input_hash or sha256(user)
        key = cache_key(stage, prompt_version, sha256(system), model, params, input_hash)
        path = self.cache_dir / stage / f"{key}.json"

        with self.tracer.span("llm.complete", stage=stage, model=model, prompt_version=prompt_version) as span:
            if path.exists():
                entry = json.loads(path.read_text())
                out = schema.model_validate(entry["parsed"])
                self.tracer.record(span, cache_hit=True)
                return out, {**_meta(entry), "cache_hit": True, "key": key}
            if self.mode == "replay":
                raise CacheMiss(
                    f"replay mode: no cached result for stage={stage} prompt={prompt_version} model={model} "
                    f"key={key[:12]}. Run with TI_MODE=live and an OpenRouter key to create it."
                )
            entry = self._call_live(stage, prompt_version, model, system, user, schema, params)
            entry["key"] = key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
            self.tracer.record(span, cache_hit=False, usage=entry.get("usage"))
            return schema.model_validate(entry["parsed"]), {**_meta(entry), "cache_hit": False, "key": key}

    # ---- live call -----------------------------------------------------------------------
    def _openai(self) -> Any:
        if self._client is None:
            key = os.getenv("OPENROUTER_API_KEY")
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in.")
            from openai import OpenAI

            self._client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)
        return self._client

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _create(self, **kwargs: Any) -> Any:
        """One API call with retries and exponential backoff on rate limits, connection errors and 5xx."""
        from openai import APIConnectionError, APIStatusError, RateLimitError

        for attempt in range(1, self.max_attempts + 1):
            self._throttle()
            try:
                return self._openai().chat.completions.create(**kwargs)
            except (RateLimitError, APIConnectionError) as e:
                err: Exception = e
            except APIStatusError as e:
                if e.status_code < 500:
                    raise
                err = e
            if attempt == self.max_attempts:
                raise err
            time.sleep(min(2**attempt, 30))
        raise RuntimeError("unreachable")

    def _call_live(
        self, stage: str, prompt_version: str, model: str, system: str, user: str, schema: type[T], params: dict
    ) -> dict:
        from openai import BadRequestError

        extra: dict[str, Any] = {"usage": {"include": True}}  # ask OpenRouter to return the billed cost
        if params.get("provider_order"):
            extra["provider"] = {"order": params["provider_order"], "allow_fallbacks": False}
        if params.get("reasoning_effort"):
            extra["reasoning"] = {"effort": params["reasoning_effort"]}
        base = dict(model=model, temperature=params["temperature"], max_tokens=params["max_tokens"], extra_body=extra)
        if params.get("seed") is not None:
            base["seed"] = params["seed"]
        t0 = time.monotonic()
        schema_json = schema.model_json_schema()
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        mode_used = "json_schema"
        try:
            resp = self._create(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "strict": True, "schema": schema_json},
                },
                **base,
            )
        except BadRequestError:
            # Model/provider does not support structured output: JSON mode, schema described in the prompt.
            mode_used = "json_object"
            messages = [
                {"role": "system", "content": system + "\n\nReturn only JSON matching this schema:\n" + json.dumps(schema_json)},
                {"role": "user", "content": user},
            ]
            resp = self._create(messages=messages, response_format={"type": "json_object"}, **base)

        parsed, text, err = _parse(resp, schema)
        retried = False
        if parsed is None:  # one retry on invalid JSON / schema violation
            retried = True
            messages = messages + [
                {"role": "assistant", "content": text or ""},
                {"role": "user", "content": f"That was invalid ({err}). Return only valid JSON matching the schema."},
            ]
            resp = self._create(messages=messages, response_format={"type": "json_object"}, **base)
            parsed, text, err = _parse(resp, schema)
            if parsed is None:
                u = getattr(resp, "usage", None)
                raise InvalidOutput(
                    f"{stage}: model returned invalid output twice: {err}",
                    text=text,
                    usage=u.model_dump() if hasattr(u, "model_dump") else None,
                    latency_s=time.monotonic() - t0,
                )

        usage = getattr(resp, "usage", None)
        return {
            "stage": stage,
            "prompt_version": prompt_version,
            "model_requested": model,
            "params": params,
            "structured_mode": mode_used,
            "retried": retried,
            "request": {"system": system, "user": user},
            "response_text": text,
            "parsed": parsed.model_dump(),
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else (dict(usage) if usage else None),
            "latency_s": round(time.monotonic() - t0, 3),
            "finish_reason": getattr(resp.choices[0], "finish_reason", None),
            "model_returned": getattr(resp, "model", None),
            "provider_returned": (getattr(resp, "model_extra", None) or {}).get("provider"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _parse(resp: Any, schema: type[T]) -> tuple[T | None, str, str]:
    text = resp.choices[0].message.content or ""
    try:
        return schema.model_validate_json(_strip_fence(text)), text, ""
    except (ValidationError, ValueError) as e:
        return None, text, str(e)[:300]


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


def _meta(entry: dict) -> dict:
    return {
        "model_returned": entry.get("model_returned"),
        "provider_returned": entry.get("provider_returned"),
        "usage": entry.get("usage"),
        "timestamp": entry.get("timestamp"),
        "latency_s": entry.get("latency_s"),
        "finish_reason": entry.get("finish_reason"),
        "retried": entry.get("retried"),
        "structured_mode": entry.get("structured_mode"),
    }
