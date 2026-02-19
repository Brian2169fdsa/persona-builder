"""
SQLAlchemy ORM Models

Maps to the PostgreSQL schema in db/schema.sql.
Tables: personas, persona_artifacts.
All enum-like columns use plain TEXT — no PostgreSQL enum types.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Persona(Base):
    __tablename__ = "personas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    role = Column(Text)
    description = Column(Text)
    status = Column(Text, nullable=False, default="draft")
    confidence_score = Column(Float)
    confidence_grade = Column(Text)
    spec_valid = Column(Boolean)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    deployed_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)

    artifacts = relationship(
        "PersonaArtifact", back_populates="persona",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_personas_slug_version"),
    )


class PersonaArtifact(Base):
    __tablename__ = "persona_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type = Column(Text, nullable=False)
    content_json = Column(JSONB)
    content_text = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    persona = relationship("Persona", back_populates="artifacts")

    __table_args__ = (
        UniqueConstraint(
            "persona_id", "artifact_type",
            name="uq_persona_artifacts_persona_type",
        ),
    )
