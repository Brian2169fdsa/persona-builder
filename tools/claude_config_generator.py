"""
Claude Config Generator

Generates an Anthropic Claude API-compatible configuration from a persona spec
and system prompt. Output is ready to use with the Anthropic Messages API.

Input:
    spec (dict) — normalized persona spec
    system_prompt (str) — generated system prompt
Output:
    dict — Claude API config

Deterministic. No network calls. No AI reasoning.
"""

import os


# Tone → temperature mapping (Claude uses 0.0–1.0)
TONE_TEMPERATURE = {
    "professional": 0.3,
    "formal": 0.2,
    "authoritative": 0.2,
    "neutral": 0.4,
    "friendly": 0.5,
    "empathetic": 0.5,
    "casual": 0.7,
    "playful": 0.8,
}

# Response length → max_tokens mapping
LENGTH_TOKENS = {
    "concise": 512,
    "moderate": 1024,
    "detailed": 2048,
}


def generate_claude_config(spec, system_prompt):
    """Generate an Anthropic Claude Messages API config.

    Args:
        spec: Normalized persona spec dict.
        system_prompt: The system prompt string.

    Returns:
        dict — Claude config with model, system, parameters.
    """
    personality = spec.get("personality", {})
    behavior = spec.get("behavior", {})
    guardrails = spec.get("guardrails", {})
    persona = spec.get("persona", {})

    tone = personality.get("tone", "professional")
    temperature = TONE_TEMPERATURE.get(tone, 0.4)

    response_length = behavior.get("response_length", "concise")
    max_tokens = min(
        LENGTH_TOKENS.get(response_length, 1024),
        guardrails.get("max_response_tokens", 1024),
    )

    # Top_k for controlling diversity (lower = more focused)
    top_k = 40 if tone in ("casual", "playful", "friendly") else 20

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_k": top_k,
        "system": system_prompt,
        "messages": [],
        "metadata": {
            "persona_name": persona.get("name", "Unknown"),
            "persona_slug": persona.get("slug", "unknown"),
            "persona_role": persona.get("role", "AI Assistant"),
            "tone": tone,
            "response_length": response_length,
        },
    }


# --- Self-check ---
if __name__ == "__main__":
    from tools.persona_normalizer import normalize_persona
    from tools.system_prompt_generator import generate_system_prompt

    print("=== Claude Config Generator Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full config generation
    print("Test 1: Full Claude config generation")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "traits": ["empathetic"],
        "tone": "friendly",
        "knowledge_domains": ["onboarding"],
        "response_length": "concise",
        "max_response_tokens": 800,
    }
    spec = normalize_persona(raw, created_at=fixed_ts)
    prompt = generate_system_prompt(spec)
    config = generate_claude_config(spec, prompt)

    assert config["model"] == os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    assert config["temperature"] == 0.5
    assert config["max_tokens"] == 512
    assert config["top_k"] == 40  # friendly = creative
    assert isinstance(config["system"], str)
    assert "Rebecka" in config["system"]
    assert config["messages"] == []
    assert config["metadata"]["persona_name"] == "Rebecka"
    print(f"  Model: {config['model']}")
    print(f"  Temperature: {config['temperature']}")
    print(f"  Max tokens: {config['max_tokens']}")
    print("  [OK]")

    # Test 2: Formal persona
    print("\nTest 2: Formal persona → low temperature, low top_k")
    raw2 = {"name": "Daniel", "tone": "formal", "response_length": "detailed"}
    spec2 = normalize_persona(raw2, created_at=fixed_ts)
    prompt2 = generate_system_prompt(spec2)
    config2 = generate_claude_config(spec2, prompt2)
    assert config2["temperature"] == 0.2
    assert config2["top_k"] == 20
    print(f"  Temperature: {config2['temperature']}, top_k: {config2['top_k']}")
    print("  [OK]")

    # Test 3: System prompt is in config (not messages)
    print("\nTest 3: System prompt location")
    assert "system" in config
    assert config["messages"] == []
    assert len(config["system"]) > 50
    print("  [OK] System prompt in 'system' field, messages empty")

    # Test 4: Determinism
    print("\nTest 4: Determinism")
    c4a = generate_claude_config(spec, prompt)
    c4b = generate_claude_config(spec, prompt)
    assert c4a == c4b
    print("  [OK]")

    print("\n=== All claude_config_generator checks passed ===")
