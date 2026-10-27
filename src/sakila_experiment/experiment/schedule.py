from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import asdict, dataclass

from ..artifacts import canonical_json, sha256_bytes
from ..config import ExperimentConfig
from ..contracts import DatasetError, Question


@dataclass(frozen=True)
class TrialAssignment:
    trial_id: str
    question_id: str
    complexity: str
    scenario_id: str
    repetition_id: int
    inference_seed: int
    schedule_position: int


def inference_seed(base: int, question_id: str, repetition_id: int) -> int:
    digest = hashlib.sha256(f"{base}:{question_id}:{repetition_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 2147483647


def build_schedule(questions: tuple[Question, ...], settings: ExperimentConfig, *, pilot: bool = False) -> tuple[TrialAssignment, ...]:
    if len({question.question_id for question in questions}) != len(questions):
        raise DatasetError("Duplicate question IDs in trial plan")
    if pilot:
        if not questions or any(not q.question_id.startswith("P") for q in questions):
            raise DatasetError("Pilot plans require only separate P-prefixed question IDs")
        repetitions = 1
    else:
        counts = Counter(question.complexity for question in questions)
        if len(questions) != settings.question_count or counts != {label: settings.questions_per_complexity for label in ("simple", "medium", "complex")}:
            raise DatasetError("Main dataset must contain 30 questions, ten per complexity")
        if any(not question.question_id.startswith("Q") for question in questions):
            raise DatasetError("Main plans require Q-prefixed question IDs")
        repetitions = settings.repetitions
    generator = random.Random(settings.order_seed)
    assignments = []
    for repetition in range(1, repetitions + 1):
        block = [(question, scenario) for question in sorted(questions, key=lambda q: q.question_id) for scenario in settings.scenario_ids]
        generator.shuffle(block)
        for question, scenario in block:
            assignments.append(TrialAssignment(
                trial_id=f"{question.question_id}-{scenario}-r{repetition:02d}",
                question_id=question.question_id, complexity=question.complexity,
                scenario_id=scenario, repetition_id=repetition,
                inference_seed=inference_seed(settings.inference_seed_base, question.question_id, repetition),
                schedule_position=len(assignments) + 1,
            ))
    return tuple(assignments)


def schedule_document(assignments: tuple[TrialAssignment, ...], settings: ExperimentConfig, *, pilot: bool) -> dict:
    trials = [asdict(trial) for trial in assignments]
    return {"plan_version": 1, "mode": "pilot" if pilot else "main", "generation_executed": False,
            "trial_count": len(trials), "settings": settings.model_dump(mode="json"),
            "trials_sha256": sha256_bytes(canonical_json(trials)), "trials": trials}

