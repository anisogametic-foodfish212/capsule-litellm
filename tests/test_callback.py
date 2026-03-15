# Copyright 2026 Quantum Pipes Technologies, LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the CapsuleLogger LiteLLM callback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from capsule_litellm.callback import (
    CapsuleLogger,
    _duration_ms,
    _extract_request,
    _hash_messages,
    _parse_response,
    _RESULT_TRUNCATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    content: str = "Hello!",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    model: str = "gpt-4o",
) -> SimpleNamespace:
    """Build a minimal object that looks like litellm.ModelResponse."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    return SimpleNamespace(choices=[choice], usage=usage, model=model, id="resp-1")


def _make_kwargs(
    model: str = "gpt-4o",
    messages: list[dict] | None = None,
    call_type: str = "completion",
) -> dict:
    if messages is None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"},
        ]
    return {"model": model, "messages": messages, "call_type": call_type}


# ---------------------------------------------------------------------------
# Unit tests: _extract_request
# ---------------------------------------------------------------------------


class TestExtractRequest:
    def test_last_user_message(self):
        msgs = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "Answer"},
            {"role": "user", "content": "Follow-up"},
        ]
        assert _extract_request(msgs) == "Follow-up"

    def test_no_user_message(self):
        msgs = [{"role": "system", "content": "System only"}]
        assert _extract_request(msgs) == ""

    def test_empty_messages(self):
        assert _extract_request([]) == ""

    def test_single_user_message(self):
        msgs = [{"role": "user", "content": "Hello"}]
        assert _extract_request(msgs) == "Hello"

    def test_non_string_content_converted(self):
        msgs = [{"role": "user", "content": ["structured", "content"]}]
        result = _extract_request(msgs)
        assert isinstance(result, str)
        assert "structured" in result

    def test_missing_content_key(self):
        msgs = [{"role": "user"}]
        assert _extract_request(msgs) == ""

    def test_none_content(self):
        msgs = [{"role": "user", "content": None}]
        result = _extract_request(msgs)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Unit tests: _hash_messages
# ---------------------------------------------------------------------------


class TestHashMessages:
    def test_deterministic(self):
        msgs = [{"role": "user", "content": "Hello"}]
        h1 = _hash_messages(msgs)
        h2 = _hash_messages(msgs)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_messages_different_hash(self):
        h1 = _hash_messages([{"role": "user", "content": "Hello"}])
        h2 = _hash_messages([{"role": "user", "content": "World"}])
        assert h1 != h2

    def test_sha3_256_length(self):
        h = _hash_messages([])
        assert len(h) == 64

    def test_order_matters(self):
        msgs_a = [{"role": "user", "content": "A"}, {"role": "user", "content": "B"}]
        msgs_b = [{"role": "user", "content": "B"}, {"role": "user", "content": "A"}]
        assert _hash_messages(msgs_a) != _hash_messages(msgs_b)

    def test_unicode_messages(self):
        msgs = [{"role": "user", "content": "café ☃ 東京"}]
        h = _hash_messages(msgs)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# Unit tests: _duration_ms
# ---------------------------------------------------------------------------


class TestDurationMs:
    def test_normal(self):
        start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = start + timedelta(seconds=1.5)
        assert _duration_ms(start, end) == 1500

    def test_zero(self):
        t = datetime(2026, 1, 1, tzinfo=UTC)
        assert _duration_ms(t, t) == 0

    def test_negative_clamped(self):
        start = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)
        end = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert _duration_ms(start, end) == 0

    def test_sub_millisecond(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = start + timedelta(microseconds=500)
        assert _duration_ms(start, end) == 0

    def test_large_duration(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=1)
        assert _duration_ms(start, end) == 3_600_000

    def test_non_datetime_returns_zero(self):
        assert _duration_ms("not a datetime", "also not") == 0


# ---------------------------------------------------------------------------
# Unit tests: _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_success(self):
        resp = _make_response(content="Paris", prompt_tokens=10, completion_tokens=3)
        text, t_in, t_out, err = _parse_response(resp, success=True)
        assert text == "Paris"
        assert t_in == 10
        assert t_out == 3
        assert err is None

    def test_failure(self):
        text, t_in, t_out, err = _parse_response(
            Exception("timeout"), success=False
        )
        assert text == ""
        assert t_in == 0
        assert t_out == 0
        assert "timeout" in err

    def test_failure_none(self):
        _, _, _, err = _parse_response(None, success=False)
        assert err == "Unknown error"

    def test_success_no_choices(self):
        resp = SimpleNamespace(
            choices=[], usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0)
        )
        text, _, _, _ = _parse_response(resp, success=True)
        assert isinstance(text, str)

    def test_success_none_content(self):
        message = SimpleNamespace(content=None)
        choice = SimpleNamespace(message=message)
        usage = SimpleNamespace(prompt_tokens=5, completion_tokens=0)
        resp = SimpleNamespace(choices=[choice], usage=usage)
        text, t_in, _, _ = _parse_response(resp, success=True)
        assert text == ""
        assert t_in == 5

    def test_success_no_usage_attribute(self):
        message = SimpleNamespace(content="OK")
        choice = SimpleNamespace(message=message)
        resp = SimpleNamespace(choices=[choice])
        text, t_in, t_out, _ = _parse_response(resp, success=True)
        assert text == "OK"
        assert t_in == 0
        assert t_out == 0

    def test_success_none_response(self):
        text, t_in, t_out, err = _parse_response(None, success=True)
        assert text == ""
        assert err is None


# ---------------------------------------------------------------------------
# Integration tests: CapsuleLogger
# ---------------------------------------------------------------------------


class TestCapsuleLogger:
    @pytest.fixture()
    def mock_capsules(self):
        c = MagicMock()
        c.chain = MagicMock()
        c.seal = MagicMock()
        c.storage = MagicMock()
        return c

    def test_success_creates_capsule(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules, agent_id="test-agent")

        start = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        end = start + timedelta(seconds=2)

        logger.log_success_event(
            _make_kwargs(), _make_response(), start, end
        )

        mock_capsules.chain.append.assert_called_once()
        mock_capsules.seal.seal.assert_called_once()
        mock_capsules.storage.store.assert_called_once()

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.trigger.source == "litellm"
        assert capsule.trigger.request == "What is 2+2?"
        assert capsule.trigger.timestamp == start
        assert capsule.context.agent_id == "test-agent"
        assert capsule.context.environment["model"] == "gpt-4o"
        assert capsule.context.environment["call_type"] == "completion"
        assert capsule.reasoning.model == "gpt-4o"
        assert len(capsule.reasoning.prompt_hash) == 64
        assert capsule.execution.duration_ms == 2000
        assert capsule.execution.tool_calls[0]["tool"] == "litellm.completion"
        assert capsule.execution.tool_calls[0]["success"] is True
        assert capsule.outcome.status == "success"
        assert capsule.outcome.error is None

    def test_failure_creates_capsule(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)

        start = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        end = start + timedelta(milliseconds=100)

        logger.log_failure_event(
            _make_kwargs(), Exception("rate_limit"), start, end
        )

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.outcome.status == "failure"
        assert "rate_limit" in capsule.outcome.error
        assert capsule.execution.duration_ms == 100
        assert capsule.execution.tool_calls[0]["success"] is False

    def test_call_order_is_chain_then_seal_then_store(self, mock_capsules):
        """Chain append, then seal, then store -- ordering matters for hash chaining."""
        logger = CapsuleLogger(capsules=mock_capsules)
        start = datetime(2026, 3, 1, tzinfo=UTC)

        call_order = []
        mock_capsules.chain.append.side_effect = lambda c: call_order.append("chain")
        mock_capsules.seal.seal.side_effect = lambda c: call_order.append("seal")
        mock_capsules.storage.store.side_effect = lambda c: call_order.append("store")

        logger.log_success_event(_make_kwargs(), _make_response(), start, start)
        assert call_order == ["chain", "seal", "store"]

    def test_swallow_errors_default(self, mock_capsules):
        mock_capsules.chain.append.side_effect = RuntimeError("boom")
        logger = CapsuleLogger(capsules=mock_capsules)

        start = datetime(2026, 3, 1, tzinfo=UTC)
        logger.log_success_event(_make_kwargs(), _make_response(), start, start)

    def test_swallow_errors_false(self, mock_capsules):
        mock_capsules.chain.append.side_effect = RuntimeError("boom")
        logger = CapsuleLogger(capsules=mock_capsules, swallow_errors=False)

        start = datetime(2026, 3, 1, tzinfo=UTC)
        with pytest.raises(RuntimeError, match="boom"):
            logger.log_success_event(
                _make_kwargs(), _make_response(), start, start
            )

    def test_custom_domain_and_type(self, mock_capsules):
        from qp_capsule import CapsuleType

        logger = CapsuleLogger(
            capsules=mock_capsules,
            domain="finance",
            capsule_type=CapsuleType.AGENT,
        )

        start = datetime(2026, 3, 1, tzinfo=UTC)
        logger.log_success_event(_make_kwargs(), _make_response(), start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.domain == "finance"

    def test_embedding_call_type(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)
        kwargs = _make_kwargs(call_type="embedding")
        start = datetime(2026, 3, 1, tzinfo=UTC)

        logger.log_success_event(kwargs, _make_response(), start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.context.environment["call_type"] == "embedding"
        assert capsule.execution.tool_calls[0]["tool"] == "litellm.embedding"

    def test_result_truncation(self, mock_capsules):
        long_content = "x" * (_RESULT_TRUNCATE + 500)
        logger = CapsuleLogger(capsules=mock_capsules)

        resp = _make_response(content=long_content)
        start = datetime(2026, 3, 1, tzinfo=UTC)
        logger.log_success_event(_make_kwargs(), resp, start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert len(capsule.outcome.result) == _RESULT_TRUNCATE
        assert len(capsule.execution.tool_calls[0]["result"]) == _RESULT_TRUNCATE

    def test_missing_messages_in_kwargs(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)
        kwargs = {"model": "gpt-4o"}
        start = datetime(2026, 3, 1, tzinfo=UTC)

        logger.log_success_event(kwargs, _make_response(), start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.trigger.request == ""
        assert capsule.execution.tool_calls[0]["arguments"]["message_count"] == 0

    def test_missing_model_in_kwargs(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)
        kwargs = {"messages": [{"role": "user", "content": "hi"}]}
        start = datetime(2026, 3, 1, tzinfo=UTC)

        logger.log_success_event(kwargs, _make_response(), start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.reasoning.model == "unknown"

    @pytest.mark.asyncio
    async def test_async_success(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)

        start = datetime(2026, 3, 1, tzinfo=UTC)
        end = start + timedelta(seconds=1)

        await logger.async_log_success_event(
            _make_kwargs(), _make_response(), start, end
        )

        mock_capsules.chain.append.assert_called_once()
        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.outcome.status == "success"
        assert capsule.execution.duration_ms == 1000

    @pytest.mark.asyncio
    async def test_async_failure(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)

        start = datetime(2026, 3, 1, tzinfo=UTC)
        await logger.async_log_failure_event(
            _make_kwargs(), Exception("500"), start, start
        )

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.outcome.status == "failure"

    @pytest.mark.asyncio
    async def test_async_swallow_errors(self, mock_capsules):
        mock_capsules.chain.append.side_effect = RuntimeError("async boom")
        logger = CapsuleLogger(capsules=mock_capsules)
        start = datetime(2026, 3, 1, tzinfo=UTC)

        await logger.async_log_success_event(
            _make_kwargs(), _make_response(), start, start
        )

    def test_token_metrics(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)

        resp = _make_response(prompt_tokens=500, completion_tokens=200)
        start = datetime(2026, 3, 1, tzinfo=UTC)
        logger.log_success_event(_make_kwargs(), resp, start, start)

        capsule = mock_capsules.chain.append.call_args[0][0]
        assert capsule.outcome.metrics["tokens_in"] == 500
        assert capsule.outcome.metrics["tokens_out"] == 200
        assert capsule.outcome.metrics["latency_ms"] == 0
        assert capsule.execution.resources_used["tokens_in"] == 500
        assert capsule.execution.resources_used["tokens_out"] == 200

    def test_prompt_hash_determinism(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)

        kwargs = _make_kwargs()
        start = datetime(2026, 3, 1, tzinfo=UTC)

        logger.log_success_event(kwargs, _make_response(), start, start)
        hash1 = mock_capsules.chain.append.call_args[0][0].reasoning.prompt_hash

        logger.log_success_event(kwargs, _make_response(), start, start)
        hash2 = mock_capsules.chain.append.call_args[0][0].reasoning.prompt_hash

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_multiple_calls_create_separate_capsules(self, mock_capsules):
        logger = CapsuleLogger(capsules=mock_capsules)
        start = datetime(2026, 3, 1, tzinfo=UTC)

        logger.log_success_event(_make_kwargs(), _make_response(), start, start)
        logger.log_success_event(
            _make_kwargs(model="claude-3"), _make_response(), start, start
        )

        assert mock_capsules.chain.append.call_count == 2
        assert mock_capsules.seal.seal.call_count == 2
        assert mock_capsules.storage.store.call_count == 2


class TestExtractRequestEdgeCases:
    def test_non_string_content(self):
        msgs = [{"role": "user", "content": ["text block", {"type": "image"}]}]
        result = _extract_request(msgs)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_content_key(self):
        msgs = [{"role": "user"}]
        assert _extract_request(msgs) == ""

    def test_unicode_content(self):
        msgs = [{"role": "user", "content": "cafe\u0301 ☃"}]
        assert _extract_request(msgs) == "cafe\u0301 ☃"


class TestParseResponseEdgeCases:
    def test_no_usage_attribute(self):
        resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
        text, t_in, t_out, err = _parse_response(resp, success=True)
        assert text == "ok"
        assert t_in == 0
        assert t_out == 0

    def test_none_content(self):
        msg = SimpleNamespace(content=None)
        choice = SimpleNamespace(message=msg)
        usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1)
        resp = SimpleNamespace(choices=[choice], usage=usage)
        text, _, _, _ = _parse_response(resp, success=True)
        assert text == ""

    def test_success_none_response(self):
        text, t_in, t_out, err = _parse_response(None, success=True)
        assert text == ""
        assert err is None
