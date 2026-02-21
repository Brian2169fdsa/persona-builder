"""
OpenAI Config Generator

Generates an OpenAI API-compatible configuration from a persona spec
and system prompt. Output is ready to use with the OpenAI Chat Completions API.

Input:
    spec (dict) — normalized persona spec
    system_prompt (str) — generated system prompt
Output:
    dict — OpenAI API config

Deterministic. No network calls. No AI reasoning.
"""

import os


# Tone → temperature mapping
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


def generate_openai_config(spec, system_prompt):
    """Generate an OpenAI Chat Completions API config.

    Args:
        spec: Normalized persona spec dict.
        system_prompt: The system prompt string.

    Returns:
        dict — OpenAI config with model, messages, parameters.
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

    # Higher top_p for more creative personas
    top_p = 0.9 if tone in ("casual", "playful", "friendly") else 0.8

    # Frequency penalty to reduce repetition
    frequency_penalty = 0.3 if response_length == "concise" else 0.1

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": 0.1,
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

    print("=== OpenAI Config Generator Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"

    # Test 1: Full config generation
    print("Test 1: Full OpenAI config generation")
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
    config = generate_openai_config(spec, prompt)

    assert config["model"] == os.environ.get("OPENAI_MODEL", "gpt-4o")
    assert config["temperature"] == 0.5  # friendly → 0.5
    assert config["max_tokens"] == 512   # min(concise=512, max=800)
    assert config["top_p"] == 0.9        # friendly = creative
    assert len(config["messages"]) == 1
    assert config["messages"][0]["role"] == "system"
    assert "Rebecka" in config["messages"][0]["content"]
    assert config["metadata"]["persona_name"] == "Rebecka"
    print(f"  Model: {config['model']}")
    print(f"  Temperature: {config['temperature']}")
    print(f"  Max tokens: {config['max_tokens']}")
    print("  [OK]")

    # Test 2: Formal persona has lower temperature
    print("\nTest 2: Formal persona → low temperature")
    raw2 = {"name": "Daniel", "tone": "formal", "response_length": "detailed"}
    spec2 = normalize_persona(raw2, created_at=fixed_ts)
    prompt2 = generate_system_prompt(spec2)
    config2 = generate_openai_config(spec2, prompt2)
    assert config2["temperature"] == 0.2
    assert config2["top_p"] == 0.8
    assert config2["max_tokens"] == 1024  # min(detailed=2048, default max=1024)
    print(f"  Temperature: {config2['temperature']}")
    print("  [OK]")

    # Test 3: max_response_tokens caps max_tokens
    print("\nTest 3: max_response_tokens cap")
    raw3 = {"name": "Sarah", "response_length": "detailed", "max_response_tokens": 500}
    spec3 = normalize_persona(raw3, created_at=fixed_ts)
    prompt3 = generate_system_prompt(spec3)
    config3 = generate_openai_config(spec3, prompt3)
    assert config3["max_tokens"] == 500  # min(2048, 500)
    print(f"  Max tokens: {config3['max_tokens']} (capped by guardrail)")
    print("  [OK]")

    # Test 4: Determinism
    print("\nTest 4: Determinism")
    c4a = generate_openai_config(spec, prompt)
    c4b = generate_openai_config(spec, prompt)
    assert c4a == c4b
    print("  [OK]")

    print("\n=== All openai_config_generator checks passed ===")
