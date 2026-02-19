"""
Persona Version Manager

Manages persona versions on the filesystem. Reads existing versions
from the output directory and determines the next version number.

Input:
    slug (str) — persona slug
    output_root (str) — root output directory
Output:
    dict — version info

Deterministic. No network calls. No AI reasoning.
"""

import os
import json
import re


VERSION_DIR_PATTERN = re.compile(r"^v(\d+)$")


def get_persona_versions(slug, output_root="output"):
    """Get all versions of a persona from the filesystem.

    Args:
        slug: Persona slug (kebab-case).
        output_root: Root output directory.

    Returns:
        dict with slug, versions list, latest_version, next_version.
    """
    persona_dir = os.path.join(output_root, slug)

    versions = []
    if os.path.isdir(persona_dir):
        for entry in sorted(os.listdir(persona_dir)):
            match = VERSION_DIR_PATTERN.match(entry)
            if match and os.path.isdir(os.path.join(persona_dir, entry)):
                version_num = int(match.group(1))
                version_info = _read_version_info(persona_dir, entry, version_num)
                versions.append(version_info)

    versions.sort(key=lambda v: v["version"])

    latest = versions[-1]["version"] if versions else 0
    next_version = latest + 1

    return {
        "slug": slug,
        "versions": versions,
        "total_versions": len(versions),
        "latest_version": latest,
        "next_version": next_version,
    }


def get_next_version(slug, output_root="output"):
    """Get the next version number for a persona.

    Args:
        slug: Persona slug.
        output_root: Root output directory.

    Returns:
        int — next version number.
    """
    info = get_persona_versions(slug, output_root)
    return info["next_version"]


def list_all_personas(output_root="output"):
    """List all personas that have at least one version on disk.

    Args:
        output_root: Root output directory.

    Returns:
        list of dicts with slug, total_versions, latest_version.
    """
    personas = []
    if not os.path.isdir(output_root):
        return personas

    for entry in sorted(os.listdir(output_root)):
        entry_path = os.path.join(output_root, entry)
        if os.path.isdir(entry_path) and not entry.startswith("_"):
            info = get_persona_versions(entry, output_root)
            if info["total_versions"] > 0:
                personas.append({
                    "slug": info["slug"],
                    "total_versions": info["total_versions"],
                    "latest_version": info["latest_version"],
                })

    return personas


def _read_version_info(persona_dir, version_dir, version_num):
    """Read version metadata from a version directory.

    Args:
        persona_dir: Path to persona directory.
        version_dir: Version directory name (e.g., "v1").
        version_num: Version number (int).

    Returns:
        dict with version info.
    """
    version_path = os.path.join(persona_dir, version_dir)

    # Try to read delivery_pack.json for metadata
    pack_path = os.path.join(version_path, "delivery_pack.json")
    pack_data = {}
    if os.path.isfile(pack_path):
        try:
            with open(pack_path) as f:
                pack_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # List files in version directory
    files = []
    if os.path.isdir(version_path):
        files = sorted(f for f in os.listdir(version_path) if os.path.isfile(
            os.path.join(version_path, f)
        ))

    return {
        "version": version_num,
        "version_str": version_dir,
        "path": version_path,
        "files": files,
        "confidence_score": pack_data.get("confidence_score"),
        "confidence_grade": pack_data.get("confidence_grade"),
        "spec_valid": pack_data.get("spec_valid"),
        "persona_name": pack_data.get("persona_name"),
    }


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
    from tools.persona_delivery_packager import package_persona_delivery

    print("=== Persona Version Manager Self-Check ===\n")

    fixed_ts = "2026-02-18T12:00:00Z"
    test_output = "output/_test_versions"

    # Clean up
    if os.path.exists(test_output):
        shutil.rmtree(test_output)

    # Helper: build a full persona delivery
    def _build_persona(name, slug, version):
        raw = {
            "name": name,
            "role": "AI Assistant",
            "description": f"{name} test persona.",
            "traits": ["helpful"],
            "tone": "friendly",
            "knowledge_domains": ["general"],
            "forbidden_topics": ["secrets"],
            "greeting": f"Hi! I'm {name}.",
            "fallback": "I'm not sure.",
            "escalation_trigger": "Help",
            "response_length": "concise",
            "pii_handling": "never store",
            "max_response_tokens": 800,
            "author": "test",
            "notes": [],
        }
        spec = normalize_persona(raw, created_at=fixed_ts)
        val = validate_persona_spec(spec)
        prompt = generate_system_prompt(spec)
        oai = generate_openai_config(spec, prompt)
        claude = generate_claude_config(spec, prompt)
        suite = generate_test_suite(spec, prompt)
        conf = score_persona_confidence(spec, val, suite)
        return package_persona_delivery(
            slug=slug, version=version,
            spec=spec, system_prompt=prompt,
            openai_config=oai, claude_config=claude,
            validation_report=val, confidence=conf, test_suite=suite,
            output_root=test_output,
        )

    # Test 1: No versions yet → next is 1
    print("Test 1: No versions → next_version = 1")
    info = get_persona_versions("nonexistent", test_output)
    assert info["total_versions"] == 0
    assert info["next_version"] == 1
    print(f"  Next version: {info['next_version']}")
    print("  [OK]")

    # Test 2: Create v1, check versions
    print("\nTest 2: Create v1 → versions list has 1 entry")
    _build_persona("Rebecka", "rebecka", 1)
    info2 = get_persona_versions("rebecka", test_output)
    assert info2["total_versions"] == 1
    assert info2["latest_version"] == 1
    assert info2["next_version"] == 2
    assert info2["versions"][0]["persona_name"] == "Rebecka"
    print(f"  Versions: {info2['total_versions']}, Next: {info2['next_version']}")
    print("  [OK]")

    # Test 3: Create v2, check versions
    print("\nTest 3: Create v2 → versions list has 2 entries")
    _build_persona("Rebecka", "rebecka", 2)
    info3 = get_persona_versions("rebecka", test_output)
    assert info3["total_versions"] == 2
    assert info3["latest_version"] == 2
    assert info3["next_version"] == 3
    print(f"  Versions: {[v['version'] for v in info3['versions']]}")
    print("  [OK]")

    # Test 4: get_next_version shortcut
    print("\nTest 4: get_next_version shortcut")
    assert get_next_version("rebecka", test_output) == 3
    assert get_next_version("nonexistent", test_output) == 1
    print("  [OK]")

    # Test 5: list_all_personas
    print("\nTest 5: list_all_personas")
    _build_persona("Daniel", "daniel", 1)
    all_personas = list_all_personas(test_output)
    slugs = [p["slug"] for p in all_personas]
    assert "rebecka" in slugs
    assert "daniel" in slugs
    assert len(all_personas) == 2
    print(f"  Personas: {slugs}")
    print("  [OK]")

    # Test 6: Version files are listed
    print("\nTest 6: Version files are listed")
    v1 = info3["versions"][0]
    assert len(v1["files"]) > 0
    assert "delivery_pack.json" in v1["files"]
    print(f"  v1 files: {v1['files']}")
    print("  [OK]")

    # Clean up
    shutil.rmtree(test_output)

    print(f"\n=== All persona_version_manager checks passed ===")
