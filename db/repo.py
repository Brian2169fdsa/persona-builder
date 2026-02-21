"""
Database Repository — Persona Persistence Layer

Three public functions:
    create_persona   — insert persona with atomic version
    store_artifact   — insert a single persona artifact row
    finalize_persona — update persona row with final status and scores

Advisory lock strategy:
    pg_advisory_xact_lock(hashtext(slug))
    prevents concurrent version collisions within a single transaction.

Deterministic. No AI reasoning. No conversation context.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models import Persona, PersonaArtifact


def create_persona(db: Session, name: str, slug: str, role: str = None,
                   description: str = None, created_at=None) -> Persona:
    """Insert a persona row with the next atomic version for slug.

    Args:
        db: Active SQLAlchemy session (caller manages commit/rollback).
        name: Display name (e.g. "Rebecka").
        slug: Kebab-case slug (e.g. "rebecka").
        role: Persona role description.
        description: Short description.
        created_at: Optional datetime; defaults to utcnow.

    Returns:
        The newly created Persona ORM instance (id, version populated).
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:slug))"),
        {"slug": slug},
    )

    result = db.execute(
        text(
            "SELECT COALESCE(MAX(version), 0) + 1 "
            "FROM personas WHERE slug = :slug"
        ),
        {"slug": slug},
    )
    version = result.scalar()

    ts = created_at if isinstance(created_at, datetime) else datetime.now(timezone.utc)

    persona = Persona(
        name=name,
        slug=slug,
        version=version,
        role=role,
        description=description,
        created_at=ts,
    )
    db.add(persona)
    db.flush()
    return persona


def store_artifact(db: Session, persona_id, artifact_type: str,
                   content_json=None, content_text=None):
    """Insert a single persona artifact.

    Exactly one of content_json / content_text should be provided.
    """
    artifact = PersonaArtifact(
        persona_id=persona_id,
        artifact_type=artifact_type,
        content_json=content_json,
        content_text=content_text,
    )
    db.add(artifact)
    db.flush()


def finalize_persona(db: Session, persona_id, status: str, *,
                     confidence_score=None, confidence_grade=None,
                     spec_valid=None, failure_reason=None):
    """Update a persona row with its final status and scores."""
    persona = db.query(Persona).filter(Persona.id == persona_id).one()
    persona.status = status
    persona.confidence_score = confidence_score
    persona.confidence_grade = confidence_grade
    persona.spec_valid = spec_valid
    persona.failure_reason = failure_reason
    if status == "deployed":
        persona.deployed_at = datetime.now(timezone.utc)
    db.flush()
