"""Run one predeclared96-trial capability pilot; never dispatch a main benchmark."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sakila_experiment.analysis.report import analyze_run, audit_run
from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.evaluation.fixtures import FIXTURE_CONTAINER
from sakila_experiment.experiment.candidate_pilot import load_candidate_bundle, capability_decision, validate_candidate_sampler
from sakila_experiment.experiment.runner import run_candidate_pilot
from sakila_experiment.generation.runtime import verify_sampler

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=ROOT/'configs/qwen3-8b-pilot.toml')
    parser.add_argument('--directory',type=Path,default=ROOT/'runs/model-selection/qwen3-8b-01')
    parser.add_argument('--manifest',type=Path,default=ROOT/'data/benchmarks/model-pilot-01/manifest.json')
    parser.add_argument('--experiment-id',default='qwen3-8b-capability-01')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(); config=load_config(args.config); out=args.directory.resolve()
    if not out.is_relative_to(ROOT/'runs/model-selection'):raise ValueError('Use a separate model-selection workspace')
    load_candidate_bundle(ROOT,args.manifest)
    if args.dry_run:
        print(json.dumps({'status':'offline_candidate_inputs_verified','assigned_trials':96,'generation_requests':0,'main_experiment_allowed':False}),flush=True)
        return
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('Commit verified source before freezing candidate requests')
    backend=out/'backend/verification.json';snapshots=ROOT/'runs/revision-02/metadata/preparation-03/snapshots';pilot=out/'pilot'
    def event(stage,**values):
        row={'stage':stage,'timestamp_utc':datetime.now(timezone.utc).isoformat(),**values}
        out.mkdir(parents=True,exist_ok=True)
        with (out/'driver-events.jsonl').open('ab') as stream:
            stream.write(canonical_json(row));stream.flush();os.fsync(stream.fileno())
        print(json.dumps(row,sort_keys=True),flush=True)
    count=0
    def progress(text):
        nonlocal count
        count+=1
        if count==1 or count%8==0:
            event('candidate_trial_complete',trial_id=json.loads(text)['trial_id'],newly_completed=count)
    try:
        running=subprocess.check_output(['docker','ps','--format','{{.Names}}'],cwd=ROOT,text=True).splitlines()
        if any(n.startswith('sakila-metadata-') for n in running):raise ValueError('Metadata catalog must be stopped during pilot inference')
        if FIXTURE_CONTAINER in running:subprocess.run(['docker','stop',FIXTURE_CONTAINER],check=True,capture_output=True)
        event('freeze_capability_pilot',assigned_trials=96)
        run_candidate_pilot(config,snapshots,backend,pilot,args.experiment_id,args.manifest,freeze_only=True,progress=progress)
        event('run_capability_pilot',assigned_trials=96)
        run_candidate_pilot(config,snapshots,backend,pilot,args.experiment_id,args.manifest,progress=progress)
        manifest,rows=audit_run(pilot)
        sampler=out/'backend/sampler-verification.json'
        if not sampler.exists():verify_sampler(config,backend,pilot,sampler)
        validate_candidate_sampler(json.loads(sampler.read_bytes()),manifest,rows,
                                   sha256_bytes((pilot/'manifest.json').read_bytes()))
        analyze_run(pilot,out/'analysis')
        decision=capability_decision(rows,manifest['question_attributes'])
        decision.update(experiment_id=args.experiment_id,completed_trials=96,
                        candidate_model=manifest['backend_evidence']['model_repository'],
                        candidate_model_sha256=manifest['model_version_or_hash'],
                        protocol_sha256=sha256_bytes((ROOT/'data/benchmarks/model-pilot-01/protocol.json').read_bytes()),
                        manifest_sha256=sha256_bytes((pilot/'manifest.json').read_bytes()),
                        sampler_verification_sha256=sha256_bytes(sampler.read_bytes()),
                        human_review_complete=False,human_review_status='pending_for_new_pilot',
                        source_commit=manifest['source_version']['git_commit'],
                        inference_requests_added_after_pilot=0)
        publish_artifact(out/'capability-decision.json',canonical_json(decision))
        report=json.loads((out/'analysis/report.json').read_bytes())
        lines=['# Local model capability pilot','',
               'Engineering evidence against AI-assisted references; no main benchmark or significance selection. Human review of new pilot remains pending.','',
               '| Condition | Correct | Trials | EX (%) |','|---|---:|---:|---:|']
        for row in report['descriptive']['by_scenario']:
            lines.append(f"| {row['scenario_id']} | {row['correct']} | {row['trials']} | {row['execution_accuracy_percent']:.2f} |")
        lines+=['',f"Decision: **{decision['status']}**.",'']
        lines += [f"- {name}: {value}" for name,value in decision['checks'].items()]
        lines += ['', 'Selection uses S3 capability only; S0–S3 differences and p-values do not select a model. Prior600 main results remain unchanged.']
        publish_artifact(out/'readout.md','\n'.join(lines).encode()+b'\n')
        publish_artifact(out/'completion.json',canonical_json({'status':'candidate_pipeline_complete','assigned_trials':96,
            'main_generation_requests':0,'decision':decision['status'],'main_experiment_allowed':False,
            'sampler_verification_sha256':sha256_bytes(sampler.read_bytes()),
            'actual_results_publication':'local_only'}))
        event('candidate_pipeline_complete',decision=decision['status'],completed_trials=96)
    except Exception as error:
        event('candidate_pipeline_interrupted',error_type=type(error).__name__,error_message=str(error),automatic_retry=False)
        raise

if __name__=='__main__':main()
