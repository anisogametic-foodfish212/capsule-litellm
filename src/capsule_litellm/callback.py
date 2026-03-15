# Copyright 2026 Quantum Pipes Technologies, LLC
# SPDX-License-Identifier: Apache-2.0

"""LiteLLM callback that creates sealed Capsules for every LLM call."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from litellm.integrations.custom_logger import CustomLogger

from qp_capsule import Capsule, CapsuleType, Capsules

if TYPE_CHECKING:
    from litellm import ModelResponse

logger = logging.getLogger(__name__)

_RESULT_TRUNCATE = 2000


class CapsuleLogger(CustomLogger):
    """LiteLLM callback that seals every LLM call into a Capsule.

    Register with LiteLLM::

        import litellm
        from capsule_litellm import CapsuleLogger

        litellm.callbacks = [CapsuleLogger()]

    Every ``litellm.completion()`` / ``litellm.acompletion()`` call will
    automatically produce a sealed, hash-chained Capsule.

    Args:
        capsules: A ``Capsules`` instance for storage, chain, and seal.
                  Defaults to ``Capsules()`` (SQLite in ~/.quantumpipes/).
        agent_id: Identity recorded in each capsule's context section.
        domain: Business domain for filtering. Defaults to ``"chat"``.
        capsule_type: CapsuleType for the records. Defaults to ``CHAT``.
        swallow_errors: If True (default), capsule failures are logged
                        but do not interrupt the LLM call flow.
    """

    def __init__(
        self,
        capsules: Capsules | None = None,
        agent_id: str = "litellm",
        domain: str = "chat",
        capsule_type: CapsuleType = CapsuleType.CHAT,
        *,
        swallow_errors: bool = True,
    ):
        self._capsules = capsules or Capsules()
        self._agent_id = agent_id
        self._domain = domain
        self._capsule_type = capsule_type
        self._swallow = swallow_errors
        super().__init__()

    # --- Sync callbacks ---

    def log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: ModelResponse,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        self._record(kwargs, response_obj, start_time, end_time, success=True)

    def log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        self._record(kwargs, response_obj, start_time, end_time, success=False)

    # --- Async callbacks ---

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: ModelResponse,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        self._record(kwargs, response_obj, start_time, end_time, success=True)

    async def async_log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        self._record(kwargs, response_obj, start_time, end_time, success=False)

    # --- Core ---

    def _record(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
        *,
        success: bool,
    ) -> None:
        try:
            capsule = self._build(kwargs, response_obj, start_time, end_time, success=success)
            self._capsules.chain.append(capsule)
            self._capsules.seal.seal(capsule)
            self._capsules.storage.store(capsule)
        except Exception:
            if self._swallow:
                logger.exception("capsule-litellm: failed to record capsule")
            else:
                raise

    def _build(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
        *,
        success: bool,
    ) -> Capsule:
        messages: list[dict[str, str]] = kwargs.get("messages", [])
        model: str = kwargs.get("model", "unknown")
        call_type: str = kwargs.get("call_type", "completion")

        request = _extract_request(messages)
        prompt_hash = _hash_messages(messages)
        duration_ms = _duration_ms(start_time, end_time)

        result_text, tokens_in, tokens_out, error_msg = _parse_response(
            response_obj, success
        )

        capsule = Capsule(type=self._capsule_type, domain=self._domain)

        # Trigger
        capsule.trigger.type = "user_request"
        capsule.trigger.source = "litellm"
        capsule.trigger.timestamp = (
            start_time if isinstance(start_time, datetime) else datetime.now(UTC)
        )
        capsule.trigger.request = request

        # Context
        capsule.context.agent_id = self._agent_id
        capsule.context.environment = {
            "model": model,
            "call_type": call_type,
        }

        # Reasoning (pre-execution: what model and prompt were selected)
        capsule.reasoning.model = model
        capsule.reasoning.prompt_hash = prompt_hash
        capsule.reasoning.confidence = 0.0
        capsule.reasoning.analysis = f"LLM {call_type} via LiteLLM"
        capsule.reasoning.selected_option = call_type
        capsule.reasoning.reasoning = f"Routed to {model}"

        # Execution
        capsule.execution.tool_calls = [
            {
                "tool": f"litellm.{call_type}",
                "arguments": {"model": model, "message_count": len(messages)},
                "result": result_text[:_RESULT_TRUNCATE] if result_text else None,
                "success": success,
                "duration_ms": duration_ms,
                "error": error_msg,
            }
        ]
        capsule.execution.duration_ms = duration_ms
        capsule.execution.resources_used = {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

        # Outcome
        capsule.outcome.status = "success" if success else "failure"
        capsule.outcome.result = result_text[:_RESULT_TRUNCATE] if result_text else None
        capsule.outcome.summary = f"{'Completed' if success else 'Failed'}: {model}"
        capsule.outcome.error = error_msg
        capsule.outcome.metrics = {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": duration_ms,
        }

        return capsule


def _extract_request(messages: list[dict[str, str]]) -> str:
    """Pull the last user message as the trigger request."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            return str(content)
    return ""


def _hash_messages(messages: list[dict[str, str]]) -> str:
    """SHA3-256 of the canonical messages JSON (for prompt auditing)."""
    blob = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha3_256(blob.encode("utf-8")).hexdigest()


def _duration_ms(start: datetime, end: datetime) -> int:
    try:
        return max(0, int((end - start).total_seconds() * 1000))
    except Exception:
        return 0


def _parse_response(
    response_obj: Any, success: bool
) -> tuple[str, int, int, str | None]:
    """Extract result text, token counts, and error from a LiteLLM response."""
    result_text = ""
    tokens_in = 0
    tokens_out = 0
    error_msg: str | None = None

    if success and response_obj is not None:
        try:
            result_text = response_obj.choices[0].message.content or ""
        except (AttributeError, IndexError, TypeError):
            result_text = str(response_obj)

        try:
            usage = response_obj.usage
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
        except AttributeError:
            pass
    elif not success:
        error_msg = str(response_obj) if response_obj is not None else "Unknown error"

    return result_text, tokens_in, tokens_out, error_msg
