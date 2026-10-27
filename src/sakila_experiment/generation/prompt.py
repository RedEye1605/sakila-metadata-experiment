from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..artifacts import canonical_json, sha256_bytes
from ..contracts import GenerationInput


class PromptError(ValueError):
    pass


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class PromptArtifact:
    messages: tuple[Message, ...]
    prompt_sha256: str
    template_sha256: str
    snapshot_sha256: str

    def chat_messages(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


def build_prompt(question: GenerationInput, snapshot_payload: dict, snapshot_sha256: str, template_path: Path) -> PromptArtifact:
    if set(snapshot_payload) != {"technical_schema", "descriptions", "business_context"}:
        raise PromptError("Only approved metadata sections belong in model context")
    serialized = canonical_json(snapshot_payload)
    if sha256_bytes(serialized) != snapshot_sha256:
        raise PromptError("Snapshot content hash mismatch")
    template = template_path.read_bytes()
    messages = (
        Message("system", template.decode("utf-8")),
        Message("user", "METADATA CONTEXT\n" + serialized.decode("utf-8") + "\nUSER QUESTION\n" + question.question + "\n\nOUTPUT RULES\nReturn one read-only MySQL SQL query only."),
    )
    encoded_messages = [{"role": m.role, "content": m.content} for m in messages]
    return PromptArtifact(messages, sha256_bytes(canonical_json(encoded_messages)), sha256_bytes(template), snapshot_sha256)

