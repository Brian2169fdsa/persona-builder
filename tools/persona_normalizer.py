"""
Persona Normalizer

Transforms a raw persona definition dict into a normalized persona spec
that conforms to the canonical persona schema.

Input:
    raw (dict) — raw persona definition from user/agent
Output:
    dict — normalized persona spec

Deterministic. No network calls. No AI reasoning.
"""

import re
from datetime import datetime, timezone


SPEC_VERSION = "1.0.0"

VALID_TONES = {"friendly", "professional", "casual", "formal", "empathetic",
               "authoritative", "playful", "neutral"}

VALID_FORMALITY = {"formal", "semi-formal", "casual"}

VALID_RESPONSE_LENGTHS = {"concise", "moderate", "detailed"}

VALID_EXPERTISE_LEVELS = {"beginner", "intermediate", "expert"}


def normalize_persona(raw, created_at=None):
    """Normalize a raw persona definition into a canonical persona spec.

    Args:
        raw: Raw persona dict with name, role, traits, etc.
        created_at: Optional ISO 8601 timestamp for deterministic output.

    Returns:
        dict — normalized persona spec.
    """
    name = raw.get("name", "Unnamed")
    slug = _generate_slug(name)
    ts = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    traits = raw.get("traits") or []
    if isinstance(traits, str):
        traits = [t.strip() for t in traits.split(",") if t.strip()]

    domains = raw.get("knowledge_domains") or raw.get("domains") or []
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]

    limitations = raw.get("limitations") or []
    if isinstance(limitations, str):
        limitations = [l.strip() for l in limitations.split(",") if l.strip()]

    forbidden = raw.get("forbidden_topics") or []
    if isinstance(forbidden, str):
        forbidden = [f.strip() for f in forbidden.split(",") if f.strip()]

    tone = raw.get("tone", "professional")
    if tone not in VALID_TONES:
        tone = "professional"

    formality = raw.get("formality", "semi-formal")
    if formality not in VALID_FORMALITY:
        formality = "semi-formal"

    response_length = raw.get("response_length", "concise")
    if response_length not in VALID_RESPONSE_LENGTHS:
        response_length = "concise"

    expertise = raw.get("expertise_level", "expert")
    if expertise not in VALID_EXPERTISE_LEVELS:
        expertise = "expert"

    return {
        "spec_version": SPEC_VERSION,
        "persona": {
            "name": name,
            "slug": slug,
            "role": raw.get("role", "AI Assistant"),
            "description": raw.get("description", f"{name} is an AI assistant."),
        },
        "personality": {
            "traits": traits,
            "communication_style": raw.get("communication_style", "clear and helpful"),
            "tone": tone,
            "formality": formality,
        },
        "knowledge": {
            "domains": domains,
            "expertise_level": expertise,
            "limitations": limitations,
        },
        "behavior": {
            "greeting": raw.get("greeting", f"Hi! I'm {name}. How can I help you today?"),
            "fallback": raw.get("fallback", "I'm not sure about that. Let me connect you with someone who can help."),
            "escalation_trigger": raw.get("escalation_trigger", "Request to speak with a human"),
            "response_length": response_length,
        },
        "guardrails": {
            "forbidden_topics": forbidden,
            "pii_handling": raw.get("pii_handling", "never store"),
            "max_response_tokens": raw.get("max_response_tokens", 1024),
        },
        "metadata": {
            "created_at": ts,
            "updated_at": ts,
            "author": raw.get("author", "system"),
            "notes": raw.get("notes") or [],
        },
    }


def _generate_slug(name):
    """Convert a persona name to a kebab-case slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-") or "unnamed"


# --- Self-check ---
if __name__ == "__main__":
    print("=== Persona Normalizer Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full persona normalization
    print("Test 1: Full persona normalization")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "description": "Warm and empathetic CSM who helps with onboarding.",
        "traits": ["empathetic", "professional", "patient"],
        "communication_style": "warm and direct",
        "tone": "friendly",
        "formality": "semi-formal",
        "knowledge_domains": ["customer onboarding", "SaaS products", "account management"],
        "expertise_level": "expert",
        "limitations": ["cannot access billing systems"],
        "greeting": "Hi! I'm Rebecka, your Customer Success Manager.",
        "fallback": "Great question — let me check with my team and get back to you.",
        "response_length": "concise",
        "forbidden_topics": ["competitor pricing", "internal roadmap"],
        "max_response_tokens": 800,
        "author": "brian",
        "notes": ["Primary persona for onboarding flows"],
    }

    spec = normalize_persona(raw, created_at=fixed_ts)

    assert spec["spec_version"] == "1.0.0"
    assert spec["persona"]["name"] == "Rebecka"
    assert spec["persona"]["slug"] == "rebecka"
    assert spec["persona"]["role"] == "Customer Success Manager"
    assert spec["personality"]["tone"] == "friendly"
    assert spec["personality"]["formality"] == "semi-formal"
    assert len(spec["personality"]["traits"]) == 3
    assert len(spec["knowledge"]["domains"]) == 3
    assert spec["knowledge"]["expertise_level"] == "expert"
    assert spec["behavior"]["response_length"] == "concise"
    assert spec["guardrails"]["max_response_tokens"] == 800
    assert len(spec["guardrails"]["forbidden_topics"]) == 2
    assert spec["metadata"]["created_at"] == fixed_ts
    assert spec["metadata"]["author"] == "brian"
    print(f"  Name: {spec['persona']['name']}, Slug: {spec['persona']['slug']}")
    print(f"  Traits: {spec['personality']['traits']}")
    print("  [OK]")

    # Test 2: Minimal persona (defaults)
    print("\nTest 2: Minimal persona with defaults")
    spec2 = normalize_persona({"name": "Daniel"}, created_at=fixed_ts)
    assert spec2["persona"]["name"] == "Daniel"
    assert spec2["persona"]["slug"] == "daniel"
    assert spec2["persona"]["role"] == "AI Assistant"
    assert spec2["personality"]["tone"] == "professional"
    assert spec2["behavior"]["greeting"].startswith("Hi! I'm Daniel")
    assert spec2["guardrails"]["max_response_tokens"] == 1024
    print(f"  Role: {spec2['persona']['role']}")
    print(f"  Tone: {spec2['personality']['tone']}")
    print("  [OK]")

    # Test 3: String traits/domains parsed to lists
    print("\nTest 3: String inputs converted to lists")
    spec3 = normalize_persona({
        "name": "Sarah",
        "traits": "energetic, persuasive, confident",
        "knowledge_domains": "sales, lead qualification",
        "forbidden_topics": "competitor pricing",
    }, created_at=fixed_ts)
    assert spec3["personality"]["traits"] == ["energetic", "persuasive", "confident"]
    assert spec3["knowledge"]["domains"] == ["sales", "lead qualification"]
    assert spec3["guardrails"]["forbidden_topics"] == ["competitor pricing"]
    print(f"  Traits: {spec3['personality']['traits']}")
    print("  [OK]")

    # Test 4: Invalid enum values get defaults
    print("\nTest 4: Invalid enums fallback to defaults")
    spec4 = normalize_persona({
        "name": "Andrew",
        "tone": "INVALID",
        "formality": "INVALID",
        "response_length": "INVALID",
        "expertise_level": "INVALID",
    }, created_at=fixed_ts)
    assert spec4["personality"]["tone"] == "professional"
    assert spec4["personality"]["formality"] == "semi-formal"
    assert spec4["behavior"]["response_length"] == "concise"
    assert spec4["knowledge"]["expertise_level"] == "expert"
    print("  [OK] All invalid enums replaced with defaults")

    # Test 5: Slug generation
    print("\nTest 5: Slug generation edge cases")
    assert _generate_slug("Rebecka") == "rebecka"
    assert _generate_slug("Sarah Jane") == "sarah-jane"
    assert _generate_slug("  Andrew  ") == "andrew"
    assert _generate_slug("Mr. Daniel O'Brien") == "mr-daniel-obrien"
    assert _generate_slug("") == "unnamed"
    print("  [OK]")

    # Test 6: Determinism
    print("\nTest 6: Determinism")
    a = normalize_persona(raw, created_at=fixed_ts)
    b = normalize_persona(raw, created_at=fixed_ts)
    assert a == b
    print("  [OK]")

    print("\n=== All persona_normalizer checks passed ===")
