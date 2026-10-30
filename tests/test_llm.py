import pytest

from ti.llm import CacheMiss, LLMClient, cache_key, sha256
from ti.schemas import Stage0LLMOut


def test_cache_key_stable_and_sensitive():
    a = cache_key("stage0", "v1", "p", "m", {"temperature": 0.0}, "h")
    assert a == cache_key("stage0", "v1", "p", "m", {"temperature": 0.0}, "h")
    for changed in (
        cache_key("stage1", "v1", "p", "m", {"temperature": 0.0}, "h"),
        cache_key("stage0", "v2", "p", "m", {"temperature": 0.0}, "h"),
        cache_key("stage0", "v1", "q", "m", {"temperature": 0.0}, "h"),
        cache_key("stage0", "v1", "p", "n", {"temperature": 0.0}, "h"),
        cache_key("stage0", "v1", "p", "m", {"temperature": 0.5}, "h"),
        cache_key("stage0", "v1", "p", "m", {"temperature": 0.0}, "i"),
    ):
        assert changed != a


def test_replay_miss_raises_and_never_calls_network(tmp_path, mock_openai):
    c = LLMClient(mode="replay", cache_dir=tmp_path, openai_client=mock_openai)
    with pytest.raises(CacheMiss):
        c.complete(stage="stage0", prompt_version="v1", model="m", system="s", user="u", schema=Stage0LLMOut)
    assert mock_openai.calls == 0


def test_live_then_cache_hit_then_replay(tmp_path, mock_openai):
    kw = dict(stage="stage0", prompt_version="v1", model="m", system="s", user="opening:\nA: support hello", schema=Stage0LLMOut)
    live = LLMClient(mode="live", cache_dir=tmp_path, openai_client=mock_openai, min_interval=0)
    out, meta = live.complete(**kw)
    assert out.label == "support" and meta["cache_hit"] is False and mock_openai.calls == 1
    out2, meta2 = live.complete(**kw)
    assert meta2["cache_hit"] is True and mock_openai.calls == 1
    replay = LLMClient(mode="replay", cache_dir=tmp_path, openai_client=mock_openai)
    out3, meta3 = replay.complete(**kw)
    assert out3 == out and meta3["cache_hit"] is True


def test_cache_file_has_no_secret(tmp_path, mock_openai, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-SECRET-TEST")
    c = LLMClient(mode="live", cache_dir=tmp_path, openai_client=mock_openai, min_interval=0)
    c.complete(stage="stage0", prompt_version="v1", model="m", system="s", user="opening:\nA: x", schema=Stage0LLMOut)
    assert all("SECRET-TEST" not in p.read_text() for p in tmp_path.rglob("*.json"))


def test_missing_model_is_clear_error(tmp_path, mock_openai):
    c = LLMClient(mode="live", cache_dir=tmp_path, openai_client=mock_openai)
    with pytest.raises(ValueError, match="no model slug"):
        c.complete(stage="stage0", prompt_version="v1", model="", system="s", user="u", schema=Stage0LLMOut)


def test_tracing_flag_without_plugin_is_loud(monkeypatch):
    monkeypatch.setenv("TI_TRACING", "1")
    with pytest.raises(NotImplementedError):
        LLMClient(mode="replay")


def test_sha256_helper():
    assert sha256("a") == sha256("a") and len(sha256("a")) == 64
