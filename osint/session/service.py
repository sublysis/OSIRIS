import os
import uuid

from osint import guardrails, pipeline
from osint.input_parser.classifier import Artifact, ArtifactType, classify_line
from osint.localfiles.loader import resolve_case_path

from . import store

_STAGE_DISPATCH = {
    "fetch": (ArtifactType.URL, "fetch_urls"),
    "localfiles": (ArtifactType.FILE, "load_local_files"),
}


def create_case(cases_root, name):
    case_id = uuid.uuid4().hex[:12]
    case_dir = os.path.join(cases_root, case_id)
    os.makedirs(os.path.join(case_dir, "uploads"), exist_ok=True)
    store.init_case(case_dir, case_id, name)
    return case_id, case_dir


def resolve_case_dir(cases_root, case_id):
    case_dir = os.path.join(cases_root, case_id)
    if not os.path.isdir(case_dir):
        raise FileNotFoundError(f"unknown case '{case_id}'")
    return case_dir


def add_artifact(case_dir, art_type, value, added_via):
    art = classify_line(f"{art_type}:{value}")
    if art.type == ArtifactType.FILE:
        resolved = resolve_case_path(case_dir, art.value)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"{value} not found under {case_dir}/uploads/ - upload it first")
    artifact_id = store.add_artifact(case_dir, art.type.value, art.value, art.raw, added_via)
    return {"id": artifact_id, "type": art.type.value, "value": art.value}


def run_stage(case_dir, config, stage, confirm=False):
    if stage not in _STAGE_DISPATCH:
        store.append_audit(case_dir, "agent", f"run_stage:{stage}", "blocked - unknown stage", False)
        raise ValueError(f"unknown or not-yet-dispatchable stage '{stage}' (available: {sorted(_STAGE_DISPATCH)})")

    try:
        guardrails.require_confirmation(stage, confirm)
    except guardrails.ConfirmationRequired:
        store.append_audit(case_dir, "agent", f"run_stage:{stage}", "blocked - missing confirm", False)
        raise

    artifact_type, stage_fn_name = _STAGE_DISPATCH[stage]
    stage_fn = getattr(pipeline, stage_fn_name)
    rows = [a for a in store.list_artifacts(case_dir) if a["type"] == artifact_type.value]
    artifacts = [Artifact(ArtifactType(r["type"]), r["value"], r["raw"]) for r in rows]
    results = [{"type": r["type"], "value": r["value"], "raw": r["raw"]} for r in rows]

    if stage == "localfiles":
        outcomes = stage_fn(artifacts, case_dir, config, results)
    else:
        outcomes = stage_fn(artifacts, config, results)

    for row, entry in zip(rows, results):
        store.save_stage_result(case_dir, row["id"], stage, entry)

    store.append_audit(case_dir, "agent", f"run_stage:{stage}", f"{len(outcomes)} artifact(s)", True)
    return {"stage": stage, "results": outcomes}


def get_state(case_dir):
    artifacts = store.list_artifacts(case_dir)
    links = store.get_links(case_dir)
    return {"artifacts": artifacts, "correlation": {"targets": [], "links": links}}


def get_audit_log(case_dir):
    return store.get_audit_log(case_dir)
