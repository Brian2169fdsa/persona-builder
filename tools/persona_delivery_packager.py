"""
Persona Delivery Packager

Assembles all persona artifacts into a delivery package and writes
them to disk under output/<slug>/v<version>/.

Input:
    slug (str) — persona slug
    version (int) — version number
    spec (dict) — normalized persona spec
    system_prompt (str) — generated system prompt
    openai_config (dict) — OpenAI API config
    claude_config (dict) — Claude API config
    validation_report (dict) — validation report
    confidence (dict) — confidence report
    test_suite (dict) — test suite
Output:
    dict — delivery summary with file paths and metadata

Deterministic. No network calls. No AI reasoning.
"""

import json
import os
from datetime import datetime, timezone


def package_persona_delivery(
    slug, version, spec, system_prompt,
    openai_config, claude_config,
    validation_report, confidence, test_suite,
    output_root="output",
):
    """Package all persona artifacts into a delivery directory.

    Args:
        slug: Persona slug (kebab-case).
        version: Version number (int).
        spec: Normalized persona spec dict.
        system_prompt: System prompt string.
        openai_config: OpenAI config dict.
        claude_config: Claude config dict.
        validation_report: Validation report dict.
        confidence: Confidence report dict.
        test_suite: Test suite dict.
        output_root: Root output directory.

    Returns:
        dict — delivery summary.
    """
    version_str = f"v{version}"
    output_dir = os.path.join(output_root, slug, version_str)
    os.makedirs(output_dir, exist_ok=True)

    files_written = []

    def _write_json(filename, data):
        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        files_written.append(filename)
        return path

    def _write_text(filename, text):
        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            f.write(text)
        files_written.append(filename)
        return path

    # Write all artifacts
    _write_json("persona_spec.json", spec)
    _write_text("system_prompt.txt", system_prompt)
    _write_json("openai_config.json", openai_config)
    _write_json("claude_config.json", claude_config)
    _write_json("validation_report.json", validation_report)
    _write_json("confidence.json", confidence)
    _write_json("test_suite.json", test_suite)

    # Build delivery summary markdown
    persona = spec.get("persona", {})
    name = persona.get("name", "Unknown")
    role = persona.get("role", "AI Assistant")
    tone = spec.get("personality", {}).get("tone", "professional")
    grade = confidence.get("grade", "?")
    score = confidence.get("score", 0)
    valid = validation_report.get("valid", False)

    summary_md = f"""# Persona Delivery Summary — {name}

**Slug:** {slug}
**Version:** {version_str}
**Role:** {role}
**Tone:** {tone}
**Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Confidence
- Score: {score}
- Grade: {grade}

## Validation
- Valid: {valid}
- Errors: {len(validation_report.get("errors", []))}
- Warnings: {len(validation_report.get("warnings", []))}

## Test Coverage
- Scenarios: {test_suite.get("total_scenarios", 0)}
- Categories: {", ".join(test_suite.get("categories", {}).keys())}

## Artifacts
{chr(10).join(f"- {f}" for f in files_written)}
- delivery_summary.md

## Platform Configs
- OpenAI: model={openai_config.get("model", "?")}
- Claude: model={claude_config.get("model", "?")}

## System Prompt Preview
```
{system_prompt[:500]}{"..." if len(system_prompt) > 500 else ""}
```
"""
    _write_text("delivery_summary.md", summary_md)

    # Build delivery pack JSON (index of everything)
    delivery_pack = {
        "slug": slug,
        "version": version,
        "version_str": version_str,
        "persona_name": name,
        "persona_role": role,
        "output_dir": output_dir,
        "files": files_written,
        "confidence_score": score,
        "confidence_grade": grade,
        "spec_valid": valid,
        "total_test_scenarios": test_suite.get("total_scenarios", 0),
    }
    _write_json("delivery_pack.json", delivery_pack)

    return delivery_pack


# --- Self-check ---
if __name__ == "__main__":
    import shutil
    from tools.persona_normalizer import normalize_persona
    from tools.validate_persona_spec import validate_persona_spec
    from tools.system_prompt_generator import generate_system_prompt
    from tools.openai_config_generator import generate_openai_config
    from tools.claude_config_generator import generate_claude_config
    from tools.persona_test_suite import generate_test_suite
    from tools.persona_confidence_scorer import score_persona_confidence

    print("=== Persona Delivery Packager Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"
    test_output = "output/_test_delivery"

    # Clean up test output
    if os.path.exists(test_output):
        shutil.rmtree(test_output)

    # Test 1: Full delivery package
    print("Test 1: Full delivery package")
    raw = {
        "name": "Rebecka",
        "role": "Customer Success Manager",
        "description": "Warm CSM.",
        "traits": ["empathetic"],
        "tone": "friendly",
        "knowledge_domains": ["onboarding"],
        "forbidden_topics": ["pricing"],
        "greeting": "Hi! I'm Rebecka.",
        "fallback": "Let me check.",
        "escalation_trigger": "Speak to human",
        "response_length": "concise",
        "pii_handling": "never store",
        "max_response_tokens": 800,
        "author": "brian",
        "notes": [],
    }
    spec = normalize_persona(raw, created_at=fixed_ts)
    val = validate_persona_spec(spec)
    prompt = generate_system_prompt(spec)
    oai = generate_openai_config(spec, prompt)
    claude = generate_claude_config(spec, prompt)
    suite = generate_test_suite(spec, prompt)
    conf = score_persona_confidence(spec, val, suite)

    pack = package_persona_delivery(
        slug="rebecka", version=1,
        spec=spec, system_prompt=prompt,
        openai_config=oai, claude_config=claude,
        validation_report=val, confidence=conf, test_suite=suite,
        output_root=test_output,
    )

    assert pack["slug"] == "rebecka"
    assert pack["version"] == 1
    assert pack["persona_name"] == "Rebecka"
    assert len(pack["files"]) == 9  # 7 artifacts + summary + delivery_pack
    assert os.path.isdir(os.path.join(test_output, "rebecka", "v1"))
    print(f"  Files: {pack['files']}")
    print(f"  Output: {pack['output_dir']}")
    print("  [OK]")

    # Test 2: All files exist on disk
    print("\nTest 2: All files exist on disk")
    for f in pack["files"]:
        path = os.path.join(test_output, "rebecka", "v1", f)
        assert os.path.isfile(path), f"Missing: {path}"
    print(f"  All {len(pack['files'])} files present")
    print("  [OK]")

    # Test 3: JSON files are valid
    print("\nTest 3: JSON files are valid JSON")
    json_files = [f for f in pack["files"] if f.endswith(".json")]
    for f in json_files:
        path = os.path.join(test_output, "rebecka", "v1", f)
        with open(path) as fh:
            data = json.load(fh)
            assert isinstance(data, dict)
    print(f"  {len(json_files)} JSON files validated")
    print("  [OK]")

    # Test 4: Delivery summary contains persona name
    print("\nTest 4: Delivery summary references persona")
    summary_path = os.path.join(test_output, "rebecka", "v1", "delivery_summary.md")
    with open(summary_path) as f:
        summary = f.read()
    assert "Rebecka" in summary
    assert "Customer Success Manager" in summary
    print("  [OK]")

    # Clean up
    shutil.rmtree(test_output)

    # Test 5: Determinism (structure, not timestamps)
    print("\nTest 5: Determinism (pack structure)")
    pack_a = package_persona_delivery(
        slug="rebecka", version=1,
        spec=spec, system_prompt=prompt,
        openai_config=oai, claude_config=claude,
        validation_report=val, confidence=conf, test_suite=suite,
        output_root=test_output,
    )
    pack_b = package_persona_delivery(
        slug="rebecka", version=1,
        spec=spec, system_prompt=prompt,
        openai_config=oai, claude_config=claude,
        validation_report=val, confidence=conf, test_suite=suite,
        output_root=test_output,
    )
    assert pack_a["files"] == pack_b["files"]
    assert pack_a["slug"] == pack_b["slug"]
    assert pack_a["version"] == pack_b["version"]
    print("  [OK]")

    # Clean up
    shutil.rmtree(test_output)

    print(f"\n=== All persona_delivery_packager checks passed ===")
