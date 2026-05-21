from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_management_summary_ui_has_no_visible_placeholder_copy():
    management_page = _read("app/pages/6_management_summary.py")

    assert "LLM summary extension placeholder" not in management_page
    assert "extension placeholder" not in management_page


def test_template_selection_does_not_label_implemented_templates_as_planned():
    template_selection_page = _read("app/pages/7_template_selection.py")

    assert "planned for a future implementation" not in template_selection_page
    assert "Logistics planned" not in template_selection_page
    assert "Finance planned" not in template_selection_page


def test_public_docs_do_not_advertise_missing_screenshots():
    public_docs = "\n".join(
        [
            _read("README.md"),
            _read("FEATURE_REPORT.md"),
            _read("APP_WALKTHROUGH.md"),
        ]
    )

    forbidden_phrases = [
        "screenshots are not committed",
        "screenshots are missing",
        "screenshots will be added",
        "screenshot placeholder",
    ]
    lowered = public_docs.lower()
    for phrase in forbidden_phrases:
        assert phrase not in lowered
