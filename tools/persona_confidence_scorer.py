"""
Persona Confidence Scorer

Calculates a confidence score and grade for a persona build based on
how complete and well-defined the persona spec is.

Input:
    spec (dict) — normalized persona spec
    validation_report (dict) — output from validate_persona_spec
    test_suite (dict) — output from generate_test_suite
Output:
    dict — confidence report with score, grade, breakdown

Deterministic. No network calls. No AI reasoning.
"""


GRADE_THRESHOLDS = [
    (0.90, "A"),
    (0.80, "B"),
    (0.65, "C"),
    (0.50, "D"),
    (0.00, "F"),
]


def score_persona_confidence(spec, validation_report, test_suite):
    """Calculate confidence score for a persona build.

    Args:
        spec: Normalized persona spec dict.
        validation_report: Output from validate_persona_spec.
        test_suite: Output from generate_test_suite.

    Returns:
        dict — confidence report with score, grade, breakdown, flags.
    """
    breakdown = {}
    flags = []

    # --- 1. Validation score (30%) ---
    checks_run = validation_report.get("checks_run", 1)
    checks_passed = validation_report.get("checks_passed", 0)
    validation_ratio = checks_passed / max(checks_run, 1)
    validation_score = validation_ratio * 0.30

    if not validation_report.get("valid", False):
        flags.append({
            "severity": "high",
            "message": f"Validation failed with {len(validation_report.get('errors', []))} errors",
        })

    num_warnings = len(validation_report.get("warnings", []))
    if num_warnings > 0:
        flags.append({
            "severity": "low",
            "message": f"Validation has {num_warnings} warning(s)",
        })

    breakdown["validation"] = {
        "weight": 0.30,
        "raw_score": round(validation_ratio, 4),
        "weighted_score": round(validation_score, 4),
    }

    # --- 2. Spec completeness (30%) ---
    completeness_checks = 0
    completeness_passed = 0

    persona = spec.get("persona", {})
    personality = spec.get("personality", {})
    knowledge = spec.get("knowledge", {})
    behavior = spec.get("behavior", {})
    guardrails = spec.get("guardrails", {})

    fields = [
        ("persona.name", bool(persona.get("name"))),
        ("persona.role", bool(persona.get("role"))),
        ("persona.description", bool(persona.get("description"))),
        ("personality.traits", len(personality.get("traits", [])) > 0),
        ("personality.tone", bool(personality.get("tone"))),
        ("personality.communication_style", bool(personality.get("communication_style"))),
        ("knowledge.domains", len(knowledge.get("domains", [])) > 0),
        ("knowledge.expertise_level", bool(knowledge.get("expertise_level"))),
        ("behavior.greeting", bool(behavior.get("greeting"))),
        ("behavior.fallback", bool(behavior.get("fallback"))),
        ("behavior.escalation_trigger", bool(behavior.get("escalation_trigger"))),
        ("guardrails.forbidden_topics", len(guardrails.get("forbidden_topics", [])) > 0),
        ("guardrails.pii_handling", bool(guardrails.get("pii_handling"))),
    ]

    for field_name, present in fields:
        completeness_checks += 1
        if present:
            completeness_passed += 1
        else:
            flags.append({
                "severity": "medium" if "name" in field_name or "role" in field_name else "low",
                "message": f"{field_name} is missing or empty",
            })

    completeness_ratio = completeness_passed / max(completeness_checks, 1)
    completeness_score = completeness_ratio * 0.30

    breakdown["completeness"] = {
        "weight": 0.30,
        "raw_score": round(completeness_ratio, 4),
        "weighted_score": round(completeness_score, 4),
        "fields_present": completeness_passed,
        "fields_total": completeness_checks,
    }

    # --- 3. Test coverage (20%) ---
    total_scenarios = test_suite.get("total_scenarios", 0)
    # 8 scenarios = full coverage; scale linearly
    max_scenarios = 8
    coverage_ratio = min(total_scenarios / max_scenarios, 1.0)
    coverage_score = coverage_ratio * 0.20

    if total_scenarios < 5:
        flags.append({
            "severity": "medium",
            "message": f"Only {total_scenarios} test scenarios generated (expected 5-8)",
        })

    breakdown["test_coverage"] = {
        "weight": 0.20,
        "raw_score": round(coverage_ratio, 4),
        "weighted_score": round(coverage_score, 4),
        "scenarios": total_scenarios,
    }

    # --- 4. Guardrail strength (20%) ---
    guardrail_checks = 0
    guardrail_passed = 0

    # Has forbidden topics defined
    guardrail_checks += 1
    if len(guardrails.get("forbidden_topics", [])) > 0:
        guardrail_passed += 1

    # Has PII handling policy
    guardrail_checks += 1
    if guardrails.get("pii_handling") in ("never store", "anonymize", "encrypt"):
        guardrail_passed += 1

    # Has token limit set
    guardrail_checks += 1
    max_tokens = guardrails.get("max_response_tokens", 0)
    if isinstance(max_tokens, int) and 1 <= max_tokens <= 16384:
        guardrail_passed += 1

    # Has escalation trigger
    guardrail_checks += 1
    if bool(behavior.get("escalation_trigger")):
        guardrail_passed += 1

    # Has fallback behavior
    guardrail_checks += 1
    if bool(behavior.get("fallback")):
        guardrail_passed += 1

    guardrail_ratio = guardrail_passed / max(guardrail_checks, 1)
    guardrail_score = guardrail_ratio * 0.20

    if guardrail_ratio < 0.6:
        flags.append({
            "severity": "high",
            "message": "Weak guardrails — fewer than 60% of safety checks pass",
        })

    breakdown["guardrails"] = {
        "weight": 0.20,
        "raw_score": round(guardrail_ratio, 4),
        "weighted_score": round(guardrail_score, 4),
        "checks_passed": guardrail_passed,
        "checks_total": guardrail_checks,
    }

    # --- Final score ---
    total_score = (
        validation_score + completeness_score +
        coverage_score + guardrail_score
    )
    total_score = round(min(total_score, 1.0), 4)

    grade = "F"
    for threshold, g in GRADE_THRESHOLDS:
        if total_score >= threshold:
            grade = g
            break

    return {
        "score": total_score,
        "grade": grade,
        "breakdown": breakdown,
        "flags": flags,
        "high_severity_flags": [f for f in flags if f["severity"] == "high"],
    }


# --- Self-check ---
if __name__ == "__main__":
    from tools.persona_normalizer import normalize_persona
    from tools.validate_persona_spec import validate_persona_spec
    from tools.system_prompt_generator import generate_system_prompt
    from tools.persona_test_suite import generate_test_suite

    print("=== Persona Confidence Scorer Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full persona → high confidence
    print("Test 1: Full persona → high confidence (A or B)")
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
    val = validate_persona_spec(spec)
    prompt = generate_system_prompt(spec)
    suite = generate_test_suite(spec, prompt)
    conf = score_persona_confidence(spec, val, suite)

    assert conf["score"] >= 0.80
    assert conf["grade"] in ("A", "B")
    assert len(conf["high_severity_flags"]) == 0
    print(f"  Score: {conf['score']}, Grade: {conf['grade']}")
    print(f"  Flags: {len(conf['flags'])}")
    print("  [OK]")

    # Test 2: Minimal persona → lower confidence
    print("\nTest 2: Minimal persona → lower confidence")
    spec2 = normalize_persona({"name": "Daniel"}, created_at=fixed_ts)
    val2 = validate_persona_spec(spec2)
    prompt2 = generate_system_prompt(spec2)
    suite2 = generate_test_suite(spec2, prompt2)
    conf2 = score_persona_confidence(spec2, val2, suite2)

    assert conf2["score"] < conf["score"]
    assert conf2["score"] > 0.0
    print(f"  Score: {conf2['score']}, Grade: {conf2['grade']}")
    print(f"  Flags: {len(conf2['flags'])}")
    print("  [OK]")

    # Test 3: Breakdown structure
    print("\nTest 3: Breakdown structure")
    assert "validation" in conf["breakdown"]
    assert "completeness" in conf["breakdown"]
    assert "test_coverage" in conf["breakdown"]
    assert "guardrails" in conf["breakdown"]
    for key, section in conf["breakdown"].items():
        assert "weight" in section
        assert "raw_score" in section
        assert "weighted_score" in section
    print("  [OK] All breakdown sections present")

    # Test 4: Determinism
    print("\nTest 4: Determinism")
    c4a = score_persona_confidence(spec, val, suite)
    c4b = score_persona_confidence(spec, val, suite)
    assert c4a["score"] == c4b["score"]
    assert c4a["grade"] == c4b["grade"]
    assert c4a["breakdown"] == c4b["breakdown"]
    print("  [OK]")

    print(f"\n=== All persona_confidence_scorer checks passed ===")
