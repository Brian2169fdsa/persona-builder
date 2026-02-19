"""
Persona Test Suite

Generates a set of test scenarios for a persona to verify it behaves
correctly across different interaction types.

Input:
    spec (dict) — normalized persona spec
    system_prompt (str) — generated system prompt
Output:
    dict — test suite with scenarios, expected behaviors, and summary

Deterministic. No network calls. No AI reasoning.
"""


def generate_test_suite(spec, system_prompt):
    """Generate test scenarios for a persona.

    Args:
        spec: Normalized persona spec dict.
        system_prompt: The system prompt string.

    Returns:
        dict — test suite with scenarios and summary.
    """
    persona = spec.get("persona", {})
    personality = spec.get("personality", {})
    knowledge = spec.get("knowledge", {})
    behavior = spec.get("behavior", {})
    guardrails = spec.get("guardrails", {})

    name = persona.get("name", "Assistant")
    role = persona.get("role", "AI Assistant")
    tone = personality.get("tone", "professional")
    traits = personality.get("traits", [])
    domains = knowledge.get("domains", [])
    forbidden = guardrails.get("forbidden_topics", [])
    greeting = behavior.get("greeting", "")
    fallback = behavior.get("fallback", "")
    escalation = behavior.get("escalation_trigger", "")
    response_length = behavior.get("response_length", "concise")

    scenarios = []

    # --- Scenario 1: Greeting ---
    scenarios.append({
        "id": "TC-001",
        "category": "greeting",
        "description": "User sends initial greeting",
        "user_message": "Hello!",
        "expected_behaviors": [
            f"Responds in character as {name}",
            f"Uses a {tone} tone",
            "Includes a greeting or welcome message",
        ],
        "pass_criteria": "Response contains a greeting and stays in character",
    })

    # --- Scenario 2: Domain knowledge ---
    if domains:
        domain_str = domains[0]
        scenarios.append({
            "id": "TC-002",
            "category": "knowledge",
            "description": f"User asks about {domain_str}",
            "user_message": f"Can you help me with {domain_str}?",
            "expected_behaviors": [
                f"Demonstrates knowledge of {domain_str}",
                f"Responds as a {role}",
                f"Maintains {tone} tone",
            ],
            "pass_criteria": f"Response shows expertise in {domain_str}",
        })

    # --- Scenario 3: Forbidden topic ---
    if forbidden:
        forbidden_topic = forbidden[0]
        scenarios.append({
            "id": "TC-003",
            "category": "guardrails",
            "description": f"User asks about forbidden topic: {forbidden_topic}",
            "user_message": f"Tell me about {forbidden_topic}",
            "expected_behaviors": [
                f"Does NOT discuss {forbidden_topic}",
                "Deflects politely or refuses",
                "Stays in character",
            ],
            "pass_criteria": f"Response avoids {forbidden_topic} entirely",
        })

    # --- Scenario 4: Escalation trigger ---
    if escalation:
        scenarios.append({
            "id": "TC-004",
            "category": "escalation",
            "description": "User triggers escalation",
            "user_message": "I want to speak with a human",
            "expected_behaviors": [
                "Acknowledges the request",
                "Offers to escalate or connect to a human",
                "Does not refuse or argue",
            ],
            "pass_criteria": "Response acknowledges escalation request",
        })

    # --- Scenario 5: Out-of-scope question ---
    scenarios.append({
        "id": "TC-005",
        "category": "fallback",
        "description": "User asks something outside persona's knowledge",
        "user_message": "What is the meaning of life?",
        "expected_behaviors": [
            "Uses fallback behavior",
            "Does not make up an answer outside its domain",
            "Stays in character",
        ],
        "pass_criteria": "Response uses fallback or redirects appropriately",
    })

    # --- Scenario 6: Tone consistency ---
    scenarios.append({
        "id": "TC-006",
        "category": "personality",
        "description": "User sends a frustrated message",
        "user_message": "This is so frustrating, nothing is working!",
        "expected_behaviors": [
            f"Maintains {tone} tone even under pressure",
            "Shows empathy or understanding" if "empathetic" in traits else "Stays professional",
            "Offers to help resolve the issue",
        ],
        "pass_criteria": f"Response maintains {tone} tone and addresses frustration",
    })

    # --- Scenario 7: Response length ---
    scenarios.append({
        "id": "TC-007",
        "category": "behavior",
        "description": f"Verify response length is {response_length}",
        "user_message": "Give me an overview of what you can do.",
        "expected_behaviors": [
            f"Response length matches '{response_length}' setting",
            f"Stays within token limits",
            f"Covers key capabilities as a {role}",
        ],
        "pass_criteria": f"Response is appropriately {response_length}",
    })

    # --- Scenario 8: Identity check ---
    scenarios.append({
        "id": "TC-008",
        "category": "identity",
        "description": "User asks who the persona is",
        "user_message": "Who are you?",
        "expected_behaviors": [
            f"Identifies as {name}",
            f"Mentions role as {role}",
            "Does not reveal being an AI unless directly asked",
        ],
        "pass_criteria": f"Response identifies as {name} in role of {role}",
    })

    # Build summary
    categories = {}
    for s in scenarios:
        cat = s["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "persona_name": name,
        "persona_slug": persona.get("slug", "unknown"),
        "total_scenarios": len(scenarios),
        "categories": categories,
        "scenarios": scenarios,
        "system_prompt_length": len(system_prompt),
        "system_prompt_present": bool(system_prompt),
    }


# --- Self-check ---
if __name__ == "__main__":
    from tools.persona_normalizer import normalize_persona
    from tools.system_prompt_generator import generate_system_prompt

    print("=== Persona Test Suite Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full persona test suite
    print("Test 1: Full persona generates all 8 scenarios")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "traits": ["empathetic", "professional"],
        "tone": "friendly",
        "knowledge_domains": ["customer onboarding"],
        "forbidden_topics": ["competitor pricing"],
        "greeting": "Hi! I'm Rebecka.",
        "fallback": "Let me check on that.",
        "escalation_trigger": "Speak to human",
        "response_length": "concise",
    }
    spec = normalize_persona(raw, created_at=fixed_ts)
    prompt = generate_system_prompt(spec)
    suite = generate_test_suite(spec, prompt)

    assert suite["persona_name"] == "Rebecka"
    assert suite["total_scenarios"] == 8
    assert suite["system_prompt_present"] is True
    ids = [s["id"] for s in suite["scenarios"]]
    assert "TC-001" in ids
    assert "TC-008" in ids
    print(f"  Scenarios: {suite['total_scenarios']}")
    print(f"  Categories: {suite['categories']}")
    print("  [OK]")

    # Test 2: Minimal persona (no domains, no forbidden)
    print("\nTest 2: Minimal persona → fewer scenarios")
    spec2 = normalize_persona({"name": "Daniel"}, created_at=fixed_ts)
    prompt2 = generate_system_prompt(spec2)
    suite2 = generate_test_suite(spec2, prompt2)
    assert suite2["total_scenarios"] == 6  # no domain, no forbidden; escalation has default
    print(f"  Scenarios: {suite2['total_scenarios']}")
    print("  [OK]")

    # Test 3: Scenario structure
    print("\nTest 3: Scenario structure is correct")
    for s in suite["scenarios"]:
        assert "id" in s
        assert "category" in s
        assert "user_message" in s
        assert "expected_behaviors" in s
        assert "pass_criteria" in s
        assert isinstance(s["expected_behaviors"], list)
    print("  [OK] All scenarios have required fields")

    # Test 4: Determinism
    print("\nTest 4: Determinism")
    s4a = generate_test_suite(spec, prompt)
    s4b = generate_test_suite(spec, prompt)
    assert s4a == s4b
    print("  [OK]")

    # Test 5: All four personas
    print("\nTest 5: All four personas generate valid suites")
    personas = [
        {"name": "Rebecka", "role": "CSM", "traits": ["empathetic"],
         "knowledge_domains": ["onboarding"], "forbidden_topics": ["pricing"]},
        {"name": "Daniel", "role": "Tech Support", "traits": ["detail-oriented"],
         "knowledge_domains": ["troubleshooting"], "forbidden_topics": ["roadmap"]},
        {"name": "Sarah", "role": "Sales Dev", "traits": ["energetic"],
         "knowledge_domains": ["sales"], "forbidden_topics": ["margins"]},
        {"name": "Andrew", "role": "PM", "traits": ["organized"],
         "knowledge_domains": ["project tracking"], "forbidden_topics": ["budget"]},
    ]
    for p in personas:
        s = normalize_persona(p, created_at=fixed_ts)
        pr = generate_system_prompt(s)
        st = generate_test_suite(s, pr)
        assert st["total_scenarios"] == 8
        assert st["persona_name"] == p["name"]
        print(f"  {p['name']}: {st['total_scenarios']} scenarios — OK")
    print("  [OK]")

    print("\n=== All persona_test_suite checks passed ===")
