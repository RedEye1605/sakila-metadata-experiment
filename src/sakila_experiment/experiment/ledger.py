"""Single-writer append-only SQLite ledger; responses survive evaluation failures."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from .schedule import TrialAssignment


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, manifest_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trials (
                experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
                trial_id TEXT NOT NULL, assignment_json TEXT NOT NULL,
                PRIMARY KEY (experiment_id, trial_id)
            );
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL, trial_id TEXT NOT NULL,
                attempt_id INTEGER NOT NULL, kind TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                FOREIGN KEY (experiment_id, trial_id) REFERENCES trials(experiment_id, trial_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_terminal_outcome
            ON events(experiment_id, trial_id) WHERE kind='trial_completed';
            CREATE UNIQUE INDEX IF NOT EXISTS one_dispatch_and_response
            ON events(experiment_id, trial_id, attempt_id, kind) WHERE kind!='infrastructure_failure';
        """)
        for table in ("experiments", "trials", "events"):
            for operation in ("UPDATE", "DELETE"):
                self.connection.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable research record'); END")

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def register(self, experiment_id: str, manifest: dict, assignments: tuple[TrialAssignment, ...]):
        if not assignments or len({a.trial_id for a in assignments}) != len(assignments):
            raise LedgerError("Trial assignments must be nonempty and unique")
        manifest_text = canonical_json(manifest).decode()
        digest = sha256_bytes(manifest_text.encode())
        expected = {a.trial_id: canonical_json(asdict(a)).decode() for a in assignments}
        with self.transaction():
            existing = self.connection.execute("SELECT manifest_sha256 FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
            if existing:
                recorded = dict(self.connection.execute("SELECT trial_id,assignment_json FROM trials WHERE experiment_id=?", (experiment_id,)))
                if existing[0] != digest or recorded != expected:
                    raise LedgerError("Resume manifest or trial plan differs from registered artifacts")
                return
            self.connection.execute("INSERT INTO experiments VALUES (?,?,?)", (experiment_id, manifest_text, digest))
            self.connection.executemany("INSERT INTO trials VALUES (?,?,?)", [(experiment_id, key, value) for key, value in expected.items()])

    def _events(self, experiment_id: str, trial_id: str):
        return self.connection.execute("SELECT attempt_id,kind,payload_json FROM events WHERE experiment_id=? AND trial_id=? ORDER BY sequence", (experiment_id, trial_id)).fetchall()

    def _append(self, experiment_id: str, trial_id: str, attempt: int, kind: str, payload: dict):
        text = canonical_json(payload).decode()
        self.connection.execute("INSERT INTO events(experiment_id,trial_id,attempt_id,kind,timestamp_utc,payload_json,payload_sha256) VALUES(?,?,?,?,?,?,?)", (experiment_id, trial_id, attempt, kind, datetime.now(timezone.utc).isoformat(), text, sha256_bytes(text.encode())))

    def start_attempt(self, experiment_id: str, trial_id: str) -> int:
        with self.transaction():
            events = self._events(experiment_id, trial_id)
            if any(kind in {"response_received", "trial_completed"} for _, kind, _ in events):
                raise LedgerError("Stored responses must be resumed without another generation")
            if events and events[-1][1] != "infrastructure_failure":
                raise LedgerError("Previous dispatch is unresolved or ambiguous; classify it explicitly before retry")
            attempt = max((row[0] for row in events), default=0) + 1
            self._append(experiment_id, trial_id, attempt, "request_started", {})
            return attempt

    def record_response(self, experiment_id: str, trial_id: str, attempt: int, response: dict):
        with self.transaction():
            events = self._events(experiment_id, trial_id)
            if not events or events[-1][:2] != (attempt, "request_started"):
                raise LedgerError("Response does not belong to the current unresolved dispatch")
            self._append(experiment_id, trial_id, attempt, "response_received", response)

    def record_infrastructure_failure(self, experiment_id: str, trial_id: str, attempt: int, details: dict):
        with self.transaction():
            events = self._events(experiment_id, trial_id)
            if not events or events[-1][0] != attempt or any(kind == "trial_completed" for _, kind, _ in events):
                raise LedgerError("Infrastructure incident does not belong to an active attempt")
            self._append(experiment_id, trial_id, attempt, "infrastructure_failure", details)

    def latest_response(self, experiment_id: str, trial_id: str) -> tuple[int, dict] | None:
        for attempt, kind, payload in reversed(self._events(experiment_id, trial_id)):
            if kind == "response_received":
                return attempt, json.loads(payload)
        return None

    def recover_dispatch(self, experiment_id: str, trial_id: str, attempt: int, *, operator: str, note: str):
        """Explicitly classify an ambiguous dispatch; never discard a response."""
        if not operator.strip() or not note.strip():
            raise LedgerError("Recovery requires an operator and an incident explanation")
        with self.transaction():
            events = self._events(experiment_id, trial_id)
            if not events or events[-1][:2] != (attempt, "request_started"):
                raise LedgerError("Only the current unresolved dispatch can be classified")
            if any(kind in {"response_received", "trial_completed"} for _, kind, _ in events):
                raise LedgerError("Stored responses and completed trials cannot be regenerated")
            self._append(experiment_id, trial_id, attempt, "infrastructure_failure",
                         {"error_type": "ambiguous_dispatch", "classification": "explicit_operator_recovery",
                          "operator": operator.strip(), "note": note.strip(), "response_available": False,
                          "retry_policy": "A later explicit run may dispatch again; exactly-once inference is not claimed"})

    def finish_trial(self, experiment_id: str, trial_id: str, attempt: int, outcome: dict):
        if type(outcome.get("execution_accuracy")) is not int or outcome["execution_accuracy"] not in {0, 1}:
            raise LedgerError("Only evaluable binary outcomes can complete a trial; infrastructure failures remain pending")
        with self.transaction():
            events = self._events(experiment_id, trial_id)
            if any(kind == "trial_completed" for _, kind, _ in events):
                raise LedgerError("Completed trials cannot be overwritten")
            if not any(number == attempt and kind == "response_received" for number, kind, _ in events):
                raise LedgerError("A durable model response is required before completing a trial")
            self._append(experiment_id, trial_id, attempt, "trial_completed", outcome)

    def completed(self, experiment_id: str) -> dict[str, dict]:
        return {trial: json.loads(payload) for trial, payload in self.connection.execute("SELECT trial_id,payload_json FROM events WHERE experiment_id=? AND kind='trial_completed'", (experiment_id,))}

    def export_jsonl(self, experiment_id: str, path: Path):
        rows = self.connection.execute("SELECT sequence,trial_id,attempt_id,kind,timestamp_utc,payload_json,payload_sha256 FROM events WHERE experiment_id=? ORDER BY sequence", (experiment_id,))
        lines = []
        for sequence, trial, attempt, kind, timestamp, payload, digest in rows:
            if sha256_bytes(payload.encode()) != digest:
                raise LedgerError("Stored event content hash mismatch")
            lines.append(canonical_json({"sequence": sequence, "experiment_id": experiment_id, "trial_id": trial, "attempt_id": attempt, "kind": kind, "timestamp_utc": timestamp, "payload": json.loads(payload), "payload_sha256": digest}))
        publish_artifact(path, b"".join(lines))

