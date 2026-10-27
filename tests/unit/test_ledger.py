import json
import sqlite3

import pytest

from sakila_experiment.config import ExperimentConfig
from sakila_experiment.contracts import Question
from sakila_experiment.experiment.ledger import Ledger, LedgerError
from sakila_experiment.experiment.schedule import build_schedule


def plan():
    return build_schedule((Question(question_id="P001", question="Berapa jumlah film untuk fixture pilot?", complexity="simple"),), ExperimentConfig(), pilot=True)


def test_response_survives_restart_and_prevents_regeneration(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    trials = plan()
    trial = trials[0].trial_id
    with Ledger(path) as ledger:
        ledger.register("pilot", {"snapshot_hash": "fixed"}, trials)
        attempt = ledger.start_attempt("pilot", trial)
        ledger.record_response("pilot", trial, attempt, {"raw_llm_response": "SELECT 1"})
    with Ledger(path) as resumed:
        resumed.register("pilot", {"snapshot_hash": "fixed"}, trials)
        assert resumed.latest_response("pilot", trial) == (attempt, {"raw_llm_response": "SELECT 1"})
        with pytest.raises(LedgerError):
            resumed.start_attempt("pilot", trial)
        resumed.finish_trial("pilot", trial, attempt, {"execution_accuracy": 0})
        with pytest.raises(LedgerError):
            resumed.finish_trial("pilot", trial, attempt, {"execution_accuracy": 1})
        assert resumed.completed("pilot")[trial]["execution_accuracy"] == 0
        resumed.export_jsonl("pilot", tmp_path / "events.jsonl")
    assert len((tmp_path / "events.jsonl").read_text().splitlines()) == 3


def test_infrastructure_failure_requires_explicit_classification_before_retry(tmp_path):
    trials = plan()
    trial = trials[0].trial_id
    with Ledger(tmp_path / "ledger.sqlite3") as ledger:
        ledger.register("pilot", {}, trials)
        attempt = ledger.start_attempt("pilot", trial)
        with pytest.raises(LedgerError):
            ledger.start_attempt("pilot", trial)
        ledger.record_infrastructure_failure("pilot", trial, attempt, {"error_type": "connection_failed"})
        assert ledger.start_attempt("pilot", trial) == attempt + 1
        assert ledger.completed("pilot") == {}


def test_database_outages_preserve_response_and_allow_multiple_incidents(tmp_path):
    trials = plan()
    trial = trials[0].trial_id
    with Ledger(tmp_path / "ledger.sqlite3") as ledger:
        ledger.register("pilot", {}, trials)
        attempt = ledger.start_attempt("pilot", trial)
        ledger.record_response("pilot", trial, attempt, {"raw_llm_response": "SELECT 1"})
        for _ in range(2):
            ledger.record_infrastructure_failure("pilot", trial, attempt, {"error_type": "database_unavailable"})
        with pytest.raises(LedgerError):
            ledger.start_attempt("pilot", trial)
        with pytest.raises(LedgerError):
            ledger.finish_trial("pilot", trial, attempt, {"execution_accuracy": None})


def test_resume_rejects_changed_manifest_and_sql_records_are_immutable(tmp_path):
    trials = plan()
    with Ledger(tmp_path / "ledger.sqlite3") as ledger:
        ledger.register("pilot", {"snapshot_hash": "first"}, trials)
        with pytest.raises(LedgerError):
            ledger.register("pilot", {"snapshot_hash": "different"}, trials)
        with pytest.raises(sqlite3.IntegrityError):
            ledger.connection.execute("UPDATE experiments SET manifest_sha256='tampered'")


def test_explicit_recovery_cannot_discard_a_saved_response(tmp_path):
    trials = plan()
    trial = trials[0].trial_id
    with Ledger(tmp_path / "ledger.sqlite3") as ledger:
        ledger.register("pilot", {}, trials)
        attempt = ledger.start_attempt("pilot", trial)
        ledger.record_response("pilot", trial, attempt, {"raw_response": "SELECT 1"})
        with pytest.raises(LedgerError):
            ledger.recover_dispatch("pilot", trial, attempt, operator="Fixture operator", note="Must not discard response")
        assert ledger.latest_response("pilot", trial) is not None

