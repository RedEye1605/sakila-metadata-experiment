"""Separate public questions, private references, and inference-safe input."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from .config import StrictModel


class DatasetError(ValueError):
    pass


class Question(StrictModel):
    question_id: str = Field(pattern=r"^[QP][0-9]{3}$")
    question: str = Field(min_length=10)
    complexity: Literal["simple", "medium", "complex"]
    schema_references: tuple[str, ...] = ()

    def generation_input(self) -> GenerationInput:
        return GenerationInput(question=self.question)


class GenerationInput(StrictModel):
    # No question ID, complexity, scenario, schema hints, or gold can cross here.
    question: str = Field(min_length=10)


class GoldReference(StrictModel):
    question_id: str = Field(pattern=r"^[QP][0-9]{3}$")
    sql: str = Field(min_length=1)
    column_count: int = Field(ge=1)
    ordered: bool = False
    approximate_columns: tuple[int, ...] = ()
    review_status: Literal["draft", "approved"] = "draft"
    semantic_notes: str = ""


def load_questions(path: Path) -> tuple[Question, ...]:
    try:
        content = path.read_bytes()
        if len(content) > 1024 * 1024:
            raise DatasetError("Question dataset exceeds the bounded size")
        rows = [Question.model_validate_json(line) for line in content.splitlines() if line.strip()]
    except (OSError, ValidationError):
        raise DatasetError("Question dataset cannot be read or fails its public schema") from None
    if not rows or len({q.question_id for q in rows}) != len(rows):
        raise DatasetError("Question IDs must be present and unique")
    if len({q.question.strip().casefold() for q in rows}) != len(rows):
        raise DatasetError("Duplicate question wording is not allowed")
    return tuple(rows)


def load_gold(path: Path) -> dict[str, GoldReference]:
    try:
        references = [GoldReference.model_validate_json(line) for line in path.read_bytes().splitlines() if line.strip()]
    except (OSError, ValidationError):
        raise DatasetError("Private references cannot be read or fail their schema") from None
    if len({q.question_id for q in references}) != len(references):
        raise DatasetError("Duplicate reference question IDs")
    return {q.question_id: q for q in references}

