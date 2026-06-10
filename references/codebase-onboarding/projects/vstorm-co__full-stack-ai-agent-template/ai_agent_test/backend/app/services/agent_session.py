"""Per-connection AI agent session (PydanticAI).

Encapsulates the orchestration that used to live in the WebSocket route:
  - holds per-connection state (history, deps, current conversation id)
  - persists user/assistant turns via shared service helpers
  - streams PydanticAI agent events back to the client over the WebSocket

The route is left as a thin lifecycle wrapper that just feeds incoming messages to
``AgentSession.process_message``.
"""

import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic_ai import (
    Agent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from pydantic_ai.messages import BinaryContent, TextPart, ThinkingPart, ThinkingPartDelta

from app.agents.assistant import Deps, get_agent
from app.api.deps import get_conversation_service
from app.db.models.user import User
from app.db.session import get_db_context
from app.services.agent import (
    build_message_history,
    persist_assistant_turn,
    persist_user_turn,
    resolve_kb_collections,
    send_event,
)
from app.services.file_storage import get_file_storage
from app.services.usage import UsageService

logger = logging.getLogger(__name__)


class AgentSession:
    """One WebSocket session with the AI agent."""

    def __init__(
        self,
        websocket: WebSocket,
        user: User,
    ) -> None:
        self.websocket = websocket
        self.user = user
        self.conversation_history: list[dict[str, str]] = []
        self.deps = Deps()
        self.current_conversation_id: str | None = None

    async def process_message(self, data: dict[str, Any]) -> None:
        """Process one user turn: persist input, run the agent, stream events, persist output."""
        user_message = data.get("message", "")
        file_ids = data.get("file_ids", [])

        if not user_message and not file_ids:
            await send_event(self.websocket, "error", {"message": "Empty message"})
            return
        self.current_conversation_id, newly_created, organization_id = await persist_user_turn(
            self.user,
            user_message,
            file_ids,
            requested_conversation_id=data.get("conversation_id"),
            current_conversation_id=self.current_conversation_id,
        )
        if newly_created and self.current_conversation_id:
            await send_event(
                self.websocket,
                "conversation_created",
                {"conversation_id": self.current_conversation_id},
            )

        await send_event(self.websocket, "user_prompt", {"content": user_message})

        try:
            assistant = get_agent(
                model_name=data.get("model"),
                thinking_effort=data.get("thinking_effort"),
            )
            model_history = build_message_history(self.conversation_history)
            user_input = await self._build_multimodal_input(user_message, file_ids)
            self.deps.kb_collection_names = await resolve_kb_collections(
                self.current_conversation_id,
                self.user.id,
                override_kb_ids=(
                    [str(i) for i in (data.get("active_knowledge_base_ids") or [])]
                    if "active_knowledge_base_ids" in data
                    and isinstance(data.get("active_knowledge_base_ids"), list)
                    else None
                ),
                organization_id=str(organization_id) if organization_id else None,
            )

            collected_tool_calls: list[dict[str, Any]] = []
            async with assistant.agent.iter(
                user_input, deps=self.deps, message_history=model_history
            ) as agent_run:
                await self._stream_agent_run(agent_run, user_message, collected_tool_calls)

            # Update in-memory history only after a complete agent run
            if agent_run.result is not None:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append(
                    {"role": "assistant", "content": agent_run.result.output}
                )
            assistant_msg_id: str | None = None
            if self.current_conversation_id and agent_run.result is not None:
                assistant_msg_id = await persist_assistant_turn(
                    self.current_conversation_id,
                    agent_run.result.output,
                    getattr(assistant, "model_name", None),
                    collected_tool_calls,
                )
            # Record usage + debit credits (best-effort).
            if agent_run.result is not None and organization_id:
                await self._record_usage(
                    agent_run=agent_run,
                    assistant=assistant,
                    organization_id=organization_id,
                )

            if assistant_msg_id:
                await send_event(
                    self.websocket,
                    "message_saved",
                    {
                        "message_id": assistant_msg_id,
                        "conversation_id": self.current_conversation_id,
                    },
                )

            await send_event(
                self.websocket,
                "complete",
                {"conversation_id": self.current_conversation_id},
            )
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.exception(f"Error processing agent request: {e}")
            await send_event(self.websocket, "error", {"message": str(e)})

    async def _record_usage(
        self,
        *,
        agent_run: Any,
        assistant: Any,
        organization_id: Any,
    ) -> None:
        """Persist a UsageEvent + debit credits for the just-finished agent run."""
        try:
            usage = agent_run.usage()
        except Exception:
            logger.exception("usage_extract_failed")
            return

        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cached_tokens = int(getattr(usage, "cache_read_tokens", 0) or 0)
        if input_tokens == 0 and output_tokens == 0:
            return

        from uuid import UUID

        try:
            org_uuid = (
                organization_id if isinstance(organization_id, UUID) else UUID(str(organization_id))
            )
        except Exception:
            logger.warning("usage_record_skipped_invalid_org_id", extra={"org": organization_id})
            return

        conv_uuid: UUID | None = None
        if self.current_conversation_id:
            try:
                conv_uuid = UUID(self.current_conversation_id)
            except Exception:
                conv_uuid = None

        try:
            async with get_db_context() as db:
                svc = UsageService(db)
                await svc.record(
                    organization_id=org_uuid,
                    actor_user_id=self.user.id,
                    conversation_id=conv_uuid,
                    model=getattr(assistant, "model_name", "") or "",
                    provider="openai",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    ai_framework="pydantic_ai",
                )
        except Exception:
            logger.exception("usage_record_failed", extra={"org_id": str(org_uuid)})

    async def _build_multimodal_input(
        self, user_message: str, file_ids: list[Any]
    ) -> str | list[Any]:
        """Fold attached images and parsed file text into the user message."""
        if not file_ids:
            return user_message

        storage = get_file_storage()
        image_parts: list[BinaryContent] = []
        file_context_parts: list[str] = []
        async with get_db_context() as file_db:
            attached_files = await get_conversation_service(file_db).list_attached_files(file_ids)
            for chat_file in attached_files:
                try:
                    if chat_file.file_type == "image":
                        file_data = await storage.load(chat_file.storage_path)
                        image_parts.append(
                            BinaryContent(data=file_data, media_type=chat_file.mime_type)
                        )
                    elif chat_file.parsed_content:
                        file_context_parts.append(
                            f"\n---\nAttached file: {chat_file.filename}\n```\n{chat_file.parsed_content}\n```"
                        )
                except Exception as e:
                    logger.warning(f"Failed to load file {chat_file.id}: {e}")

        full_text = user_message + "".join(file_context_parts)
        if image_parts:
            return [full_text, *image_parts]
        return full_text

    async def _stream_agent_run(
        self,
        agent_run: Any,
        user_message: str,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Drive the agent_run iterator, dispatching each node to its streaming helper."""
        async for node in agent_run:
            if Agent.is_user_prompt_node(node):
                prompt_text = (
                    node.user_prompt if isinstance(node.user_prompt, str) else user_message
                )
                await send_event(self.websocket, "user_prompt_processed", {"prompt": prompt_text})
            elif Agent.is_model_request_node(node):
                await send_event(self.websocket, "model_request_start", {})
                async with node.stream(agent_run.ctx) as request_stream:
                    await self._stream_request_events(request_stream)
            elif Agent.is_call_tools_node(node):
                await send_event(self.websocket, "call_tools_start", {})
                async with node.stream(agent_run.ctx) as handle_stream:
                    await self._stream_tool_events(handle_stream, collected_tool_calls)
            elif Agent.is_end_node(node) and agent_run.result is not None:
                await send_event(
                    self.websocket, "final_result", {"output": agent_run.result.output}
                )

    async def _stream_request_events(self, request_stream: Any) -> None:
        """Forward model-request events (text/thinking/tool deltas + final-result start)."""
        async for event in request_stream:
            if isinstance(event, PartStartEvent):
                await send_event(
                    self.websocket,
                    "part_start",
                    {"index": event.index, "part_type": type(event.part).__name__},
                )
                if isinstance(event.part, TextPart) and event.part.content:
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.part.content},
                    )
                elif isinstance(event.part, ThinkingPart) and event.part.content:
                    # Surface the model's reasoning trace to the UI. Anthropic +
                    # OpenAI-reasoning models emit these as the model "thinks".
                    await send_event(
                        self.websocket,
                        "thinking_delta",
                        {"index": event.index, "content": event.part.content},
                    )
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    await send_event(
                        self.websocket,
                        "text_delta",
                        {"index": event.index, "content": event.delta.content_delta},
                    )
                elif isinstance(event.delta, ThinkingPartDelta):
                    if event.delta.content_delta:
                        await send_event(
                            self.websocket,
                            "thinking_delta",
                            {"index": event.index, "content": event.delta.content_delta},
                        )
                elif isinstance(event.delta, ToolCallPartDelta):
                    await send_event(
                        self.websocket,
                        "tool_call_delta",
                        {"index": event.index, "args_delta": event.delta.args_delta},
                    )
            elif isinstance(event, FinalResultEvent):
                await send_event(
                    self.websocket,
                    "final_result_start",
                    {"tool_name": event.tool_name},
                )

    async def _stream_tool_events(
        self,
        handle_stream: Any,
        collected_tool_calls: list[dict[str, Any]],
    ) -> None:
        """Forward tool-call/result events; collect tool calls (with results) for persistence."""
        pending: dict[str, dict[str, Any]] = {}
        async for tool_event in handle_stream:
            if isinstance(tool_event, FunctionToolCallEvent):
                tc = {
                    "tool_call_id": tool_event.part.tool_call_id,
                    "tool_name": tool_event.part.tool_name,
                    "args": tool_event.part.args,
                }
                collected_tool_calls.append(tc)
                pending[tool_event.part.tool_call_id] = tc
                await send_event(self.websocket, "tool_call", tc)
            elif isinstance(tool_event, FunctionToolResultEvent):
                tc = pending.get(tool_event.tool_call_id)
                if tc is not None:
                    tc["result"] = str(tool_event.result.content)
                await send_event(
                    self.websocket,
                    "tool_result",
                    {
                        "tool_call_id": tool_event.tool_call_id,
                        "content": str(tool_event.result.content),
                    },
                )
