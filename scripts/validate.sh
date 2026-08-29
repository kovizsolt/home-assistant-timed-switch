#!/usr/bin/env bash

set -uo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly HASSFEST_IMAGE="ghcr.io/home-assistant/hassfest"

mode="all"
pull_image=true
failures=0

usage() {
    echo "Usage: $0 [all|static|tests|hassfest] [--no-pull]"
    echo
    echo "  all        Run every local validation (default)."
    echo "  static     Validate the HACS layout, JSON, YAML, and manifest metadata."
    echo "  tests      Run the repository's unit tests."
    echo "  hassfest   Run the official Hassfest Docker image."
    echo "  --no-pull  Use the locally cached Hassfest image without updating it."
}

for argument in "$@"; do
    case "${argument}" in
        all|static|tests|hassfest)
            mode="${argument}"
            ;;
        --no-pull)
            pull_image=false
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: ${argument}" >&2
            usage >&2
            exit 2
            ;;
    esac
done

run_check() {
    local name="$1"
    shift

    echo
    echo "==> ${name}"
    if "$@"; then
        echo "PASS: ${name}"
    else
        echo "FAIL: ${name}" >&2
        failures=$((failures + 1))
    fi
}

validate_static() {
    env VALIDATION_REPO_DIR="${REPO_DIR}" python3 - <<'PY'
import json
import os
import pathlib
import re
import sys

repo = pathlib.Path(os.environ["VALIDATION_REPO_DIR"])
errors = []

component_root = repo / "custom_components"
component_dirs = sorted(path for path in component_root.iterdir() if path.is_dir()) \
    if component_root.is_dir() else []
if len(component_dirs) != 1:
    errors.append("custom_components must contain exactly one integration directory")

for required_file in ("README.md", "LICENSE", "hacs.json"):
    if not (repo / required_file).is_file():
        errors.append(f"missing repository file: {required_file}")

def load_json(path):
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"invalid JSON in {path.relative_to(repo)}: {error}")
        return {}

hacs = load_json(repo / "hacs.json") if (repo / "hacs.json").is_file() else {}
if not isinstance(hacs.get("name"), str) or not hacs["name"].strip():
    errors.append("hacs.json must contain a non-empty name")
if not isinstance(hacs.get("homeassistant"), str) or not hacs["homeassistant"].strip():
    errors.append("hacs.json must contain the minimum Home Assistant version")

if len(component_dirs) == 1:
    integration_dir = component_dirs[0]
    manifest_path = integration_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    if not manifest_path.is_file():
        errors.append("integration manifest.json is missing")

    required_manifest_keys = {
        "codeowners", "documentation", "domain", "issue_tracker", "name", "version"
    }
    missing = sorted(required_manifest_keys - manifest.keys())
    if missing:
        errors.append(f"manifest.json missing keys: {', '.join(missing)}")
    if manifest.get("domain") != integration_dir.name:
        errors.append("manifest domain must match the integration directory name")
    if manifest.get("integration_type") != "helper":
        errors.append("manifest integration_type must be helper")

    version_path = repo / "VERSION"
    generated_version_path = integration_dir / "_version.py"
    version = version_path.read_text(encoding="utf-8").strip() \
        if version_path.is_file() else None
    if version is None:
        errors.append("VERSION file is missing")
    elif not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]{4}", version):
        errors.append("VERSION must use major.minor.build with a four-digit build")
    if manifest.get("version") != version:
        errors.append("manifest version must match VERSION")
    if not generated_version_path.is_file():
        errors.append("generated _version.py is missing")
    elif version is not None:
        generated_source = generated_version_path.read_text(encoding="utf-8")
        expected_assignment = f'__version__ = "{version}"'
        if expected_assignment not in generated_source:
            errors.append("_version.py version must match VERSION")
        if not re.search(
            r'^__version_time__ = "[^"T]+T[^" ]+(?:Z|[+-][0-9]{2}:[0-9]{2})"$',
            generated_source,
            re.MULTILINE,
        ):
            errors.append("_version.py must contain an ISO 8601 version timestamp with offset")

    codeowners = manifest.get("codeowners")
    if not isinstance(codeowners, list) or not codeowners \
            or any(not isinstance(owner, str) or not owner.startswith("@") for owner in codeowners):
        errors.append("manifest codeowners must contain GitHub handles starting with @")

    for key in ("documentation", "issue_tracker"):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.startswith("https://github.com/"):
            errors.append(f"manifest {key} must be a GitHub HTTPS URL")
        elif "example." in value:
            errors.append(f"manifest {key} still contains a placeholder URL")

    for relative_path in ("strings.json", "translations/en.json", "translations/hu.json"):
        path = integration_dir / relative_path
        if not path.is_file():
            errors.append(f"missing integration file: {relative_path}")
        else:
            load_json(path)

workflow_dir = repo / ".github" / "workflows"
if not workflow_dir.is_dir() or not any(workflow_dir.glob("*.yml")):
    errors.append("no GitHub Actions workflow found")

try:
    import yaml
except ImportError:
    print("NOTE: PyYAML is unavailable; workflow YAML parsing was skipped")
else:
    for pattern in ("*.yml", "*.yaml"):
        for path in workflow_dir.glob(pattern):
            try:
                with path.open(encoding="utf-8") as stream:
                    yaml.safe_load(stream)
            except (OSError, yaml.YAMLError) as error:
                errors.append(f"invalid YAML in {path.relative_to(repo)}: {error}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Local HACS structure and metadata checks passed")
PY
}

run_tests() {
    python3 -m unittest discover -s "${REPO_DIR}/tests" -v
}

run_hassfest() {
    local -a docker_arguments=(run --rm)
    if [[ "${pull_image}" == true ]]; then
        docker_arguments+=(--pull always)
    fi
    docker_arguments+=(-v "${REPO_DIR}:/github/workspace" "${HASSFEST_IMAGE}")
    docker "${docker_arguments[@]}"
}

case "${mode}" in
    all)
        run_check "Static HACS and repository validation" validate_static
        run_check "Unit tests" run_tests
        run_check "Hassfest" run_hassfest
        ;;
    static)
        run_check "Static HACS and repository validation" validate_static
        ;;
    tests)
        run_check "Unit tests" run_tests
        ;;
    hassfest)
        run_check "Hassfest" run_hassfest
        ;;
esac

echo
if ((failures > 0)); then
    echo "Validation finished with ${failures} failed check(s)." >&2
    exit 1
fi

echo "All requested validations passed."
