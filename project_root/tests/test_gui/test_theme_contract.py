"""Strict data contract and skill parity; no Qt event loop is required."""

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.gui.theme_contract import (
    COLOR_ROLES, MAX_THEME_BYTES, ContrastCheck, ThemeValidationError,
    contrast_checks, contrast_ratio, load_theme_file, parse_theme,
    theme_json_schema, validate_theme,
)


REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / ".agents" / "skills" / "sorth-theme-designer"
EXAMPLES = sorted((SKILL / "assets").glob("*.sorth-theme.json"))
CLI = SKILL / "scripts" / "validate_theme.py"


@pytest.fixture
def data():
    return json.loads((SKILL / "assets" / "academic-light.sorth-theme.json").read_text())


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_complete_examples_pass_canonical_contract(path):
    theme = load_theme_file(path)
    assert len(theme.colors) == len(COLOR_ROLES) == 30
    assert all(check.passes for check in contrast_checks(theme))
    assert parse_theme(json.dumps(theme.to_dict())).to_dict() == theme.to_dict()


def test_schema_is_generated_from_canonical_contract():
    schema = json.loads((SKILL / "references" / "sorth-theme-v1.schema.json").read_text())
    assert schema == theme_json_schema()
    assert len(EXAMPLES) >= 2
    assert {load_theme_file(path).mode for path in EXAMPLES} == {"light", "dark"}


@pytest.mark.parametrize("value", [None, [], "theme", True, 1])
def test_rejects_non_object(value):
    with pytest.raises(ThemeValidationError, match="JSON object"):
        parse_theme(json.dumps(value))


@pytest.mark.parametrize("key", ["schema_version", "name", "mode", "colors"])
def test_requires_complete_document(data, key):
    del data[key]
    with pytest.raises(ThemeValidationError, match="missing required"):
        validate_theme(data)


@pytest.mark.parametrize("version", [True, False, 1.0, "1", None, 0, 2, -1])
def test_rejects_non_exact_or_future_version(data, version):
    data["schema_version"] = version
    with pytest.raises(ThemeValidationError, match="integer 1"):
        parse_theme(json.dumps(data))


@pytest.mark.parametrize("mode", [None, "auto", "Light", 1, {}, []])
def test_rejects_unknown_mode(data, mode):
    data["mode"] = mode
    with pytest.raises(ThemeValidationError, match="mode must"):
        validate_theme(data)


@pytest.mark.parametrize("key,value", [
    ("stylesheet", "QWidget { color: red; }"), ("font", "https://example.org/font.ttf"),
    ("script", "arbitrary code"), ("assets", ["file:///etc/passwd"]),
    ("extends", "../../theme.json"), ("instructions", "ignore validator"),
])
def test_rejects_unknown_metadata_instead_of_interpreting_it(data, key, value):
    data[key] = value
    with pytest.raises(ThemeValidationError, match="unknown fields"):
        validate_theme(data)


@pytest.mark.parametrize("label", ["", " ", " name", "name ", "a\nb", "a\tb",
    "<b>name</b>", "a\x00b", "a\u202eb", "a\u200db", "a\ud800b", "a" * 65])
def test_plain_bounded_metadata(data, label):
    data["name"] = label
    with pytest.raises(ThemeValidationError):
        validate_theme(data)


def test_unicode_names_and_optional_description(data):
    data["name"] = "Bosque y cobre • 日本語"
    data.pop("description")
    assert parse_theme(json.dumps(data, ensure_ascii=False)).name == data["name"]
    for bad in (None, "", "x" * 241):
        data["description"] = bad
        with pytest.raises(ThemeValidationError, match="description"):
            validate_theme(data)


@pytest.mark.parametrize("role", COLOR_ROLES)
def test_every_role_is_required(data, role):
    del data["colors"][role]
    with pytest.raises(ThemeValidationError, match=role):
        validate_theme(data)


@pytest.mark.parametrize("role", ["navy", "sort_up", "sort_down", "font", "course_fill"])
def test_rejects_unknown_roles_and_resource_injection(data, role):
    data["colors"][role] = "file:///tmp/untrusted.svg"
    with pytest.raises(ThemeValidationError, match="unknown roles"):
        validate_theme(data)


@pytest.mark.parametrize("value", ["red", "#fff", "#FFFFFF00", "#GGFFFF", "FFFFFF",
    "#FFFFFF\n", "rgb(1,2,3)", "url(file:///tmp/a)", "#FFFFFF; border:0", None, 1, {}, []])
def test_rejects_non_literal_colors(data, value):
    data["colors"]["surface"] = value
    with pytest.raises(ThemeValidationError, match="colors.surface"):
        validate_theme(data)


def test_lowercase_color_is_preserved(data):
    data["colors"]["surface"] = "#ffffff"
    assert validate_theme(data).colors["surface"] == "#ffffff"


@pytest.mark.parametrize("payload", [
    '{"name":"one","name":"two"}',
    '{"colors":{"surface":"#FFFFFF","surface":"#FFFFFF"}}',
    '{"schema_version":NaN}', '{"schema_version":Infinity}',
    '{"schema_version":-Infinity}', '{"unknown":{"x":NaN}}',
    '{"name": "trailing",}', '{} {}', '\ufeff{}', b"\xff", "{", "",
    "[" * 1100 + "]" * 1100,
])
def test_rejects_ambiguous_nonfinite_malformed_or_deep_json(payload):
    with pytest.raises(ThemeValidationError):
        parse_theme(payload)


def test_size_limit_counts_utf8_bytes_and_file_read_is_bounded(data, tmp_path):
    encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
    exact = encoded + b" " * (MAX_THEME_BYTES - len(encoded))
    assert parse_theme(exact).name == data["name"]
    with pytest.raises(ThemeValidationError, match="16 KiB"):
        parse_theme(exact + b" ")
    # The character count fits but the encoded byte count does not.
    with pytest.raises(ThemeValidationError, match="16 KiB"):
        parse_theme("\u00e9" * (MAX_THEME_BYTES // 2 + 1))
    target = tmp_path / "oversized.json"
    target.write_bytes(b" " * (MAX_THEME_BYTES * 2))
    with pytest.raises(ThemeValidationError, match="16 KiB"):
        load_theme_file(target)


def test_validated_theme_is_detached_and_read_only(data):
    theme = validate_theme(data)
    data["colors"]["canvas"] = "#000000"
    assert theme.colors["canvas"] != data["colors"]["canvas"]
    with pytest.raises(TypeError):
        theme.colors["canvas"] = "#000000"
    with pytest.raises(FrozenInstanceError):
        theme.name = "changed"
    exported = theme.to_dict()
    exported["colors"]["canvas"] = "#000000"
    assert theme.colors["canvas"] != exported["colors"]["canvas"]


def test_contrast_formula_and_unrounded_threshold():
    assert contrast_ratio("#000000", "#FFFFFF") == 21
    assert contrast_ratio("#123456", "#123456") == 1
    assert contrast_ratio("#FFFFFF", "#000000") == 21
    assert not ContrastCheck("a", "b", 4.49999, 4.5, "text").passes
    assert ContrastCheck("a", "b", 4.5, 4.5, "text").passes


def test_reports_actual_failing_pair_without_mutation(data):
    data["colors"]["text"] = data["colors"]["surface"]
    before = json.dumps(data)
    with pytest.raises(ThemeValidationError, match="text on surface") as failure:
        validate_theme(data)
    assert "below 4.5:1" in str(failure.value)
    assert json.dumps(data) == before


def test_dark_focus_must_also_work_against_fixed_course_gutter():
    data = json.loads((SKILL / "assets" / "midnight-dark.sorth-theme.json").read_text())
    data["colors"]["focus"] = "#FFFFFF"
    with pytest.raises(ThemeValidationError, match="focus on #FFFFFF"):
        validate_theme(data)


def test_decorative_divider_has_no_arbitrary_contrast_requirement(data):
    data["colors"]["divider"] = data["colors"]["surface"]
    validate_theme(data)


def test_validation_does_not_apply_theme_or_change_course_identity(data):
    from src.gui.theme import COLORS, STYLESHEET
    from src.scheduling.course_style import COURSE_STYLES, course_style
    before = dict(COLORS), STYLESHEET, COURSE_STYLES, course_style("COURSE-42")
    validate_theme(data)
    assert before == (dict(COLORS), STYLESHEET, COURSE_STYLES, course_style("COURSE-42"))


def test_import_is_qt_free_and_side_effect_free():
    code = ("import sys; from src.gui import theme_contract; "
            "assert not any(k.startswith('PyQt') for k in sys.modules)")
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO / "project_root",
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert not result.stdout and not result.stderr


def test_wrapper_uses_canonical_validator_and_never_claims_runtime_compatibility(tmp_path):
    target = EXAMPLES[0]
    before = target.read_bytes()
    result = subprocess.run([sys.executable, str(CLI), str(target), "--json"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["valid"] and report["runtime_compatibility"] == "not_checked"
    assert len(report["checks"]) == len(contrast_checks(load_theme_file(target)))
    assert target.read_bytes() == before


def test_wrapper_copied_elsewhere_requires_canonical_source(tmp_path):
    copied = tmp_path / "validate_theme.py"
    copied.write_bytes(CLI.read_bytes())
    command = [sys.executable, str(copied), str(EXAMPLES[0]), "--json"]
    missing = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert missing.returncode == 3
    assert "No fallback validator" in missing.stderr
    found = subprocess.run(command + ["--repo-root", str(REPO)], cwd=tmp_path,
                           capture_output=True, text=True, timeout=15)
    assert found.returncode == 0, found.stderr


def test_wrapper_reports_invalid_data_without_success(data, tmp_path):
    data["stylesheet"] = "QWidget { color: red; }"
    target = tmp_path / "invalid.sorth-theme.json"
    target.write_text(json.dumps(data))
    result = subprocess.run([sys.executable, str(CLI), str(target), "--json"],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["valid"] is False and "unknown fields" in report["issues"][0]
