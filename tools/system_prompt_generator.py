"""
System Prompt Generator

Generates a platform-agnostic system prompt from a normalized persona spec.
This is the core instruction text that defines how the AI persona behaves.

Input:  spec (dict) — normalized persona spec
Output: str — system prompt text

Deterministic. No network calls. No AI reasoning.
"""


def generate_system_prompt(spec):
    """Generate a system prompt from a persona spec.

    Args:
        spec: Normalized persona spec dict.

    Returns:
        str — the complete system prompt.
    """
    persona = spec.get("persona", {})
    personality = spec.get("personality", {})
    knowledge = spec.get("knowledge", {})
    behavior = spec.get("behavior", {})
    guardrails = spec.get("guardrails", {})

    name = persona.get("name", "Assistant")
    role = persona.get("role", "AI Assistant")
    description = persona.get("description", "")

    lines = []

    # Identity
    lines.append(f"You are {name}, a {role}.")
    if description:
        lines.append(f"{description}")
    lines.append("")

    # Personality
    traits = personality.get("traits", [])
    if traits:
        lines.append(f"## Personality")
        lines.append(f"Your core traits are: {', '.join(traits)}.")
        style = personality.get("communication_style", "")
        if style:
            lines.append(f"Your communication style is {style}.")
        tone = personality.get("tone", "professional")
        formality = personality.get("formality", "semi-formal")
        lines.append(f"Maintain a {tone} tone with {formality} formality.")
        lines.append("")

    # Knowledge
    domains = knowledge.get("domains", [])
    if domains:
        lines.append("## Expertise")
        lines.append(f"You are an {knowledge.get('expertise_level', 'expert')}-level specialist in: {', '.join(domains)}.")
        limitations = knowledge.get("limitations", [])
        if limitations:
            lines.append(f"You cannot: {'; '.join(limitations)}.")
        lines.append("")

    # Behavior
    lines.append("## Behavior")
    response_length = behavior.get("response_length", "concise")
    lines.append(f"Keep responses {response_length}.")
    greeting = behavior.get("greeting", "")
    if greeting:
        lines.append(f"When greeting users, say: \"{greeting}\"")
    fallback = behavior.get("fallback", "")
    if fallback:
        lines.append(f"When you don't know the answer, say: \"{fallback}\"")
    escalation = behavior.get("escalation_trigger", "")
    if escalation:
        lines.append(f"Escalate to a human when: {escalation}.")
    lines.append("")

    # Guardrails
    forbidden = guardrails.get("forbidden_topics", [])
    pii = guardrails.get("pii_handling", "never store")
    max_tokens = guardrails.get("max_response_tokens", 1024)

    lines.append("## Rules")
    if forbidden:
        lines.append(f"NEVER discuss: {', '.join(forbidden)}.")
    lines.append(f"PII handling: {pii}.")
    lines.append(f"Keep responses under {max_tokens} tokens.")
    lines.append("Always stay in character. Never reveal that you are an AI unless directly asked.")

    return "\n".join(lines)


# --- Self-check ---
if __name__ == "__main__":
    from tools.persona_normalizer import normalize_persona

    print("=== System Prompt Generator Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full persona prompt
    print("Test 1: Full persona system prompt")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "description": "Warm and empathetic CSM who helps with onboarding.",
        "traits": ["empathetic", "professional", "patient"],
        "communication_style": "warm and direct",
        "tone": "friendly",
        "formality": "semi-formal",
        "knowledge_domains": ["customer onboarding", "SaaS products"],
        "expertise_level": "expert",
        "limitations": ["cannot access billing systems"],
        "greeting": "Hi! I'm Rebecka, your Customer Success Manager.",
        "fallback": "Great question — let me check with my team.",
        "escalation_trigger": "Request to speak with a human",
        "response_length": "concise",
        "forbidden_topics": ["competitor pricing", "internal roadmap"],
        "pii_handling": "never store",
        "max_response_tokens": 800,
    }
    spec = normalize_persona(raw, created_at=fixed_ts)
    prompt = generate_system_prompt(spec)

    assert "You are Rebecka" in prompt
    assert "Customer Success Manager" in prompt
    assert "empathetic" in prompt
    assert "customer onboarding" in prompt
    assert "cannot access billing systems" in prompt
    assert "competitor pricing" in prompt
    assert "never store" in prompt
    assert "800 tokens" in prompt
    assert "concise" in prompt
    print(f"  Prompt length: {len(prompt)} chars")
    print(f"  First line: {prompt.splitlines()[0]}")
    print("  [OK]")

    # Test 2: Minimal persona prompt
    print("\nTest 2: Minimal persona prompt")
    spec2 = normalize_persona({"name": "Daniel"}, created_at=fixed_ts)
    prompt2 = generate_system_prompt(spec2)
    assert "You are Daniel" in prompt2
    assert "AI Assistant" in prompt2
    print(f"  Prompt length: {len(prompt2)} chars")
    print("  [OK]")

    # Test 3: Determinism
    print("\nTest 3: Determinism")
    p3a = generate_system_prompt(spec)
    p3b = generate_system_prompt(spec)
    assert p3a == p3b
    print("  [OK]")

    # Test 4: All four personas
    print("\nTest 4: All four personas generate valid prompts")
    personas = [
        {"name": "Rebecka", "role": "Customer Success Manager", "traits": ["empathetic"],
         "knowledge_domains": ["onboarding"]},
        {"name": "Daniel", "role": "Technical Support Engineer", "traits": ["detail-oriented"],
         "knowledge_domains": ["troubleshooting"]},
        {"name": "Sarah", "role": "Sales Development Rep", "traits": ["energetic"],
         "knowledge_domains": ["sales"]},
        {"name": "Andrew", "role": "Project Manager", "traits": ["organized"],
         "knowledge_domains": ["project tracking"]},
    ]
    for p in personas:
        s = normalize_persona(p, created_at=fixed_ts)
        pr = generate_system_prompt(s)
        assert f"You are {p['name']}" in pr
        assert p["role"] in pr
        print(f"  {p['name']}: {len(pr)} chars — OK")
    print("  [OK]")

    print("\n=== All system_prompt_generator checks passed ===")
