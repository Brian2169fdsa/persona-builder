"""
Validate Persona Spec

Runs structural validation rules against a normalized persona spec.

Rule categories:
  PS — Persona Schema (8 rules)
  PT — Personality/Traits (4 rules)
  KD — Knowledge Domains (3 rules)
  BH — Behavior (4 rules)
  GR — Guardrails (3 rules)
  MD — Metadata (3 rules)

Input:  spec (dict) — normalized persona spec
Output: validation report dict

Deterministic. No network calls. No AI reasoning.
"""

import re
from datetime import datetime

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

VALID_TONES = {"friendly", "professional", "casual", "formal", "empathetic",
               "authoritative", "playful", "neutral"}
VALID_FORMALITY = {"formal", "semi-formal", "casual"}
VALID_RESPONSE_LENGTHS = {"concise", "moderate", "detailed"}
VALID_EXPERTISE_LEVELS = {"beginner", "intermediate", "expert"}
VALID_PII_HANDLING = {"never store", "anonymize", "encrypt"}


def validate_persona_spec(spec):
    """Run all validation rules against a persona spec.

    Args:
        spec: Normalized persona spec dict.

    Returns:
        dict with valid, errors, warnings, checks_run, checks_passed,
        checks_failed, timestamp.
    """
    errors = []
    warnings = []
    checks_run = 0
    checks_passed = 0

    def _error(rule_id, message):
        errors.append({"rule_id": rule_id, "severity": "error", "message": message})

    def _warn(rule_id, message):
        warnings.append({"rule_id": rule_id, "severity": "warning", "message": message})

    def _check(rule_id, condition, error_msg, warn_msg=None):
        nonlocal checks_run, checks_passed
        checks_run += 1
        if condition:
            checks_passed += 1
        else:
            if warn_msg:
                _warn(rule_id, warn_msg)
                checks_passed += 1  # warnings don't fail
            else:
                _error(rule_id, error_msg)

    # === PS — Persona Schema ===
    _check("PS-001", isinstance(spec.get("spec_version"), str) and
           SEMVER_PATTERN.match(spec.get("spec_version", "")),
           "spec_version must be a valid semver string")

    persona = spec.get("persona", {})
    _check("PS-002", isinstance(persona, dict) and bool(persona.get("name")),
           "persona.name is required")
    _check("PS-003", isinstance(persona.get("slug"), str) and
           SLUG_PATTERN.match(persona.get("slug", "")),
           "persona.slug must be a valid kebab-case string")
    _check("PS-004", bool(persona.get("role")),
           "persona.role is required")
    _check("PS-005", bool(persona.get("description")),
           "persona.description is required")

    _check("PS-006", isinstance(spec.get("personality"), dict),
           "personality section is required")
    _check("PS-007", isinstance(spec.get("knowledge"), dict),
           "knowledge section is required")
    _check("PS-008", isinstance(spec.get("behavior"), dict),
           "behavior section is required")

    # === PT — Personality / Traits ===
    personality = spec.get("personality", {})
    traits = personality.get("traits", [])
    _check("PT-001", isinstance(traits, list) and len(traits) > 0,
           "personality.traits must be a non-empty list",
           warn_msg="personality.traits is empty — persona may lack character definition")
    _check("PT-002", personality.get("tone") in VALID_TONES,
           f"personality.tone must be one of {sorted(VALID_TONES)}")
    _check("PT-003", personality.get("formality") in VALID_FORMALITY,
           f"personality.formality must be one of {sorted(VALID_FORMALITY)}")
    _check("PT-004", bool(personality.get("communication_style")),
           "personality.communication_style is required")

    # === KD — Knowledge Domains ===
    knowledge = spec.get("knowledge", {})
    domains = knowledge.get("domains", [])
    _check("KD-001", isinstance(domains, list) and len(domains) > 0,
           "knowledge.domains must be a non-empty list",
           warn_msg="knowledge.domains is empty — persona has no domain expertise defined")
    _check("KD-002", knowledge.get("expertise_level") in VALID_EXPERTISE_LEVELS,
           f"knowledge.expertise_level must be one of {sorted(VALID_EXPERTISE_LEVELS)}")
    _check("KD-003", isinstance(knowledge.get("limitations"), list),
           "knowledge.limitations must be a list")

    # === BH — Behavior ===
    behavior = spec.get("behavior", {})
    _check("BH-001", bool(behavior.get("greeting")),
           "behavior.greeting is required")
    _check("BH-002", bool(behavior.get("fallback")),
           "behavior.fallback is required")
    _check("BH-003", bool(behavior.get("escalation_trigger")),
           "behavior.escalation_trigger is required")
    _check("BH-004", behavior.get("response_length") in VALID_RESPONSE_LENGTHS,
           f"behavior.response_length must be one of {sorted(VALID_RESPONSE_LENGTHS)}")

    # === GR — Guardrails ===
    guardrails = spec.get("guardrails", {})
    _check("GR-001", isinstance(guardrails.get("forbidden_topics"), list),
           "guardrails.forbidden_topics must be a list")
    _check("GR-002", guardrails.get("pii_handling") in VALID_PII_HANDLING,
           f"guardrails.pii_handling must be one of {sorted(VALID_PII_HANDLING)}")
    max_tokens = guardrails.get("max_response_tokens", 0)
    _check("GR-003", isinstance(max_tokens, int) and 1 <= max_tokens <= 16384,
           "guardrails.max_response_tokens must be an integer 1–16384")

    # === MD — Metadata ===
    metadata = spec.get("metadata", {})
    _check("MD-001", bool(metadata.get("created_at")),
           "metadata.created_at is required")
    _check("MD-002", bool(metadata.get("author")),
           "metadata.author is required")
    _check("MD-003", isinstance(metadata.get("notes"), list),
           "metadata.notes must be a list")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks_run": checks_run,
        "checks_passed": checks_passed,
        "checks_failed": checks_run - checks_passed,
        "timestamp": datetime.now().isoformat(),
    }


# --- Self-check ---
if __name__ == "__main__":
    from tools.persona_normalizer import normalize_persona

    print("=== Validate Persona Spec Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Valid spec passes all checks
    print("Test 1: Valid spec passes all checks")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "description": "Warm CSM for onboarding.",
        "traits": ["empathetic", "professional"],
        "communication_style": "warm and direct",
        "tone": "friendly",
        "formality": "semi-formal",
        "knowledge_domains": ["onboarding", "SaaS"],
        "expertise_level": "expert",
        "limitations": ["no billing access"],
        "greeting": "Hi! I'm Rebecka.",
        "fallback": "Let me check on that.",
        "escalation_trigger": "Speak to human",
        "response_length": "concise",
        "forbidden_topics": ["pricing"],
        "pii_handling": "never store",
        "max_response_tokens": 800,
        "author": "brian",
        "notes": [],
    }
    spec = normalize_persona(raw, created_at=fixed_ts)
    report = validate_persona_spec(spec)
    assert report["valid"] is True, f"Expected valid, errors: {report['errors']}"
    assert report["checks_run"] == 25
    assert report["checks_failed"] == 0
    print(f"  Checks: {report['checks_passed']}/{report['checks_run']}")
    print(f"  Errors: {len(report['errors'])}, Warnings: {len(report['warnings'])}")
    print("  [OK]")

    # Test 2: Missing required fields
    print("\nTest 2: Missing required fields")
    bad_spec = {"spec_version": "bad", "persona": {}, "personality": {},
                "knowledge": {}, "behavior": {}, "guardrails": {}, "metadata": {}}
    report2 = validate_persona_spec(bad_spec)
    assert report2["valid"] is False
    assert len(report2["errors"]) >= 10
    print(f"  Errors: {len(report2['errors'])}")
    print("  [OK]")

    # Test 3: Warnings for empty optional lists
    print("\nTest 3: Warnings for empty traits and domains")
    raw3 = {
        "name": "Minimal",
        "role": "Assistant",
        "description": "Minimal persona.",
        "traits": [],
        "communication_style": "clear",
        "tone": "professional",
        "formality": "semi-formal",
        "knowledge_domains": [],
        "expertise_level": "expert",
        "limitations": [],
        "greeting": "Hello",
        "fallback": "I don't know",
        "escalation_trigger": "Help",
        "response_length": "concise",
        "forbidden_topics": [],
        "pii_handling": "never store",
        "max_response_tokens": 1024,
        "author": "system",
        "notes": [],
    }
    spec3 = normalize_persona(raw3, created_at=fixed_ts)
    report3 = validate_persona_spec(spec3)
    assert report3["valid"] is True  # Warnings don't make it invalid
    assert len(report3["warnings"]) == 2  # traits + domains
    print(f"  Warnings: {len(report3['warnings'])}")
    for w in report3["warnings"]:
        print(f"    - {w['rule_id']}: {w['message'][:60]}")
    print("  [OK]")

    # Test 4: Determinism
    print("\nTest 4: Determinism")
    r4a = validate_persona_spec(spec)
    r4b = validate_persona_spec(spec)
    assert r4a["valid"] == r4b["valid"]
    assert r4a["checks_run"] == r4b["checks_run"]
    assert r4a["errors"] == r4b["errors"]
    print("  [OK]")

    print(f"\n=== All validate_persona_spec checks passed ===")
