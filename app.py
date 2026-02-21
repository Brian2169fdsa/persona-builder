"""
Persona Builder — FastAPI Application

Endpoints:
  GET  /health                  — liveness probe
  POST /persona/assess          — raw persona → validation report + confidence preview
  POST /persona/build           — raw persona → full pipeline (normalize + validate + generate + package)
  POST /persona/test            — raw persona → test suite (no build)
  GET  /persona/{name}          — get latest version of a persona from disk
  GET  /personas                — list all personas on disk
  POST /persona/deploy          — build + write to DB (full deployment)
  GET  /persona/{name}/versions — list all versions of a persona

HTTP status codes:
  200 — success
  400 — malformed request / missing required fields
  422 — validation failure (spec invalid, confidence too low)
  404 — persona not found
  500 — internal pipeline error
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db, check_db
from db.repo import create_persona, store_artifact, finalize_persona

from tools.persona_normalizer import normalize_persona
from tools.validate_persona_spec import validate_persona_spec
from tools.system_prompt_generator import generate_system_prompt
from tools.openai_config_generator import generate_openai_config
from tools.claude_config_generator import generate_claude_config
from tools.persona_test_suite import generate_test_suite
from tools.persona_confidence_scorer import score_persona_confidence
from tools.persona_delivery_packager import package_persona_delivery
from tools.persona_version_manager import (
    get_persona_versions,
    get_next_version,
    list_all_personas,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    check_db()
    yield


app = FastAPI(
    title="Persona Builder",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow connect-hub and local dev
_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "https://internal.manageai.io,http://localhost:8080,http://localhost:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────

class PersonaRequest(BaseModel):
    """Raw persona definition for assess/build/test."""
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    traits: Optional[list] = None
    communication_style: Optional[str] = None
    tone: Optional[str] = None
    formality: Optional[str] = None
    knowledge_domains: Optional[list] = None
    expertise_level: Optional[str] = None
    limitations: Optional[list] = None
    greeting: Optional[str] = None
    fallback: Optional[str] = None
    escalation_trigger: Optional[str] = None
    response_length: Optional[str] = None
    forbidden_topics: Optional[list] = None
    pii_handling: Optional[str] = None
    max_response_tokens: Optional[int] = None
    author: Optional[str] = None
    notes: Optional[list] = None


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/persona/assess")
def assess_persona(request: PersonaRequest):
    """
    Assess a raw persona definition.
    Returns normalized spec, validation report, and confidence preview.
    Does NOT build or write anything to disk.
    """
    raw = _request_to_raw(request)

    try:
        spec = normalize_persona(raw)
        validation = validate_persona_spec(spec)
        prompt = generate_system_prompt(spec)
        suite = generate_test_suite(spec, prompt)
        confidence = score_persona_confidence(spec, validation, suite)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

    return {
        "persona_name": spec["persona"]["name"],
        "persona_slug": spec["persona"]["slug"],
        "spec_valid": validation["valid"],
        "validation": {
            "checks_run": validation["checks_run"],
            "checks_passed": validation["checks_passed"],
            "checks_failed": validation["checks_failed"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        },
        "confidence": {
            "score": confidence["score"],
            "grade": confidence["grade"],
        },
        "high_severity_flags": confidence["high_severity_flags"],
        "test_scenarios": suite["total_scenarios"],
        "hint": "Use POST /persona/build to run the full pipeline and write artifacts to disk.",
    }


@app.post("/persona/build")
def build_persona(request: PersonaRequest):
    """
    Full build pipeline: normalize → validate → generate prompts → generate configs →
    score confidence → package delivery → write to disk.
    Returns 422 if validation fails or confidence is below threshold.
    """
    raw = _request_to_raw(request)

    try:
        spec = normalize_persona(raw)
        validation = validate_persona_spec(spec)
        prompt = generate_system_prompt(spec)
        oai_config = generate_openai_config(spec, prompt)
        claude_config = generate_claude_config(spec, prompt)
        suite = generate_test_suite(spec, prompt)
        confidence = score_persona_confidence(spec, validation, suite)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")

    if not validation["valid"]:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "reason": "Validation failed",
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            },
        )

    slug = spec["persona"]["slug"]
    version = get_next_version(slug)

    try:
        pack = package_persona_delivery(
            slug=slug, version=version,
            spec=spec, system_prompt=prompt,
            openai_config=oai_config, claude_config=claude_config,
            validation_report=validation, confidence=confidence,
            test_suite=suite,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Packaging failed: {str(e)}")

    return {
        "success": True,
        "persona_name": spec["persona"]["name"],
        "slug": slug,
        "version": version,
        "output_dir": pack["output_dir"],
        "files": pack["files"],
        "confidence": {
            "score": confidence["score"],
            "grade": confidence["grade"],
        },
        "spec_valid": validation["valid"],
        "test_scenarios": suite["total_scenarios"],
    }


@app.post("/persona/test")
def test_persona(request: PersonaRequest):
    """
    Generate test scenarios for a persona without building.
    Use this to preview what test coverage looks like.
    """
    raw = _request_to_raw(request)

    try:
        spec = normalize_persona(raw)
        prompt = generate_system_prompt(spec)
        suite = generate_test_suite(spec, prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

    return {
        "persona_name": spec["persona"]["name"],
        "total_scenarios": suite["total_scenarios"],
        "categories": suite["categories"],
        "scenarios": suite["scenarios"],
    }


@app.get("/persona/{name}")
def get_persona(name: str):
    """
    Get the latest version of a persona by slug.
    Reads from the output/ directory on disk.
    """
    slug = name.lower().replace(" ", "-")
    info = get_persona_versions(slug)

    if info["total_versions"] == 0:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")

    latest = info["versions"][-1]

    return {
        "slug": slug,
        "version": latest["version"],
        "version_str": latest["version_str"],
        "path": latest["path"],
        "files": latest["files"],
        "confidence_score": latest.get("confidence_score"),
        "confidence_grade": latest.get("confidence_grade"),
        "spec_valid": latest.get("spec_valid"),
        "persona_name": latest.get("persona_name"),
        "total_versions": info["total_versions"],
    }


@app.get("/personas")
def list_personas():
    """
    List all personas that have at least one version on disk.
    """
    personas = list_all_personas()
    return {
        "total": len(personas),
        "personas": personas,
    }


@app.post("/persona/deploy")
def deploy_persona(request: PersonaRequest, db: Session = Depends(get_db)):
    """
    Full deployment pipeline: build + write to PostgreSQL.
    This is the production deployment path.
    """
    raw = _request_to_raw(request)

    try:
        spec = normalize_persona(raw)
        validation = validate_persona_spec(spec)
        prompt = generate_system_prompt(spec)
        oai_config = generate_openai_config(spec, prompt)
        claude_config = generate_claude_config(spec, prompt)
        suite = generate_test_suite(spec, prompt)
        confidence = score_persona_confidence(spec, validation, suite)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")

    if not validation["valid"]:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "reason": "Validation failed — cannot deploy",
                "errors": validation["errors"],
            },
        )

    if confidence["score"] < 0.50:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "reason": f"Confidence too low ({confidence['score']}) — cannot deploy",
                "grade": confidence["grade"],
                "flags": confidence["flags"],
            },
        )

    slug = spec["persona"]["slug"]
    name = spec["persona"]["name"]
    role = spec["persona"].get("role", "AI Assistant")
    description = spec["persona"].get("description", "")

    # Write to filesystem
    fs_version = get_next_version(slug)
    try:
        pack = package_persona_delivery(
            slug=slug, version=fs_version,
            spec=spec, system_prompt=prompt,
            openai_config=oai_config, claude_config=claude_config,
            validation_report=validation, confidence=confidence,
            test_suite=suite,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Packaging failed: {str(e)}")

    # Write to database
    try:
        persona_row = create_persona(
            db, name=name, slug=slug, role=role,
            description=description, created_at=None,
        )

        store_artifact(db, persona_row.id, "persona_spec", content_json=spec)
        store_artifact(db, persona_row.id, "system_prompt", content_text=prompt)
        store_artifact(db, persona_row.id, "openai_config", content_json=oai_config)
        store_artifact(db, persona_row.id, "claude_config", content_json=claude_config)
        store_artifact(db, persona_row.id, "validation_report", content_json=validation)
        store_artifact(db, persona_row.id, "confidence", content_json=confidence)
        store_artifact(db, persona_row.id, "test_suite", content_json=suite)
        store_artifact(db, persona_row.id, "delivery_pack", content_json=pack)

        finalize_persona(
            db, persona_row.id, status="deployed",
            confidence_score=confidence["score"],
            confidence_grade=confidence["grade"],
            spec_valid=validation["valid"],
        )

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB deploy failed: {str(e)}")

    return {
        "success": True,
        "deployed": True,
        "persona_name": name,
        "slug": slug,
        "db_version": persona_row.version,
        "fs_version": fs_version,
        "output_dir": pack["output_dir"],
        "files": pack["files"],
        "confidence": {
            "score": confidence["score"],
            "grade": confidence["grade"],
        },
        "spec_valid": validation["valid"],
        "test_scenarios": suite["total_scenarios"],
    }


@app.get("/persona/{name}/versions")
def get_persona_versions_endpoint(name: str):
    """
    List all versions of a persona by slug.
    """
    slug = name.lower().replace(" ", "-")
    info = get_persona_versions(slug)

    if info["total_versions"] == 0:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' has no versions")

    return info


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _request_to_raw(request: PersonaRequest) -> dict:
    """Convert a Pydantic request to a raw dict, dropping None values."""
    raw = {}
    data = request.model_dump()
    for key, value in data.items():
        if value is not None:
            raw[key] = value
    return raw
