import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from data_factory.field_qc_inventory import (
    CONCRETE_SURFACE_QC,
    REBAR_COUPLER_THREAD_QC,
    REBAR_MATERIAL_COUNTING,
)
from data_factory.field_qc_rules import (
    CONCRETE_SURFACE_CLASSES,
    FieldQcRulebook,
    build_default_rulebook,
    find_pending_confirmations,
    write_rulebook_outputs,
)
from scripts.build_field_qc_rulebook import main as rulebook_cli


class FieldQcRulesTests(unittest.TestCase):
    def test_default_rulebook_defines_pilot_counting_unit_and_pending_coupler_thresholds(self):
        rulebook = build_default_rulebook()

        self.assertEqual(rulebook.material_counting.unit, "bar")
        self.assertEqual(rulebook.material_counting.status, "pilot_default_pending_confirmation")
        self.assertEqual(rulebook.coupler_thread_qc.threshold_status, "requires_project_confirmation")
        self.assertEqual(rulebook.coupler_thread_qc.max_visible_threads_per_side, None)
        self.assertIn("project", rulebook.required_metadata_fields)

    def test_default_rulebook_contains_concrete_taxonomy_with_needs_review_class(self):
        rulebook = build_default_rulebook()

        self.assertEqual(rulebook.concrete_surface_qc.classes, CONCRETE_SURFACE_CLASSES)
        self.assertIn("surface_anomaly_needs_review", rulebook.concrete_surface_qc.classes)
        self.assertIn("crack", rulebook.concrete_surface_qc.classes)

    def test_guidance_is_available_for_each_first_pilot_scenario(self):
        rulebook = build_default_rulebook()

        self.assertIn("endpoint face", rulebook.capture_guidance[REBAR_MATERIAL_COUNTING].lower())
        self.assertIn("both sides", rulebook.capture_guidance[REBAR_COUPLER_THREAD_QC].lower())
        self.assertIn("overview", rulebook.capture_guidance[CONCRETE_SURFACE_QC].lower())

    def test_pending_confirmations_include_business_rules_not_model_taxonomy(self):
        pending = find_pending_confirmations(build_default_rulebook())

        self.assertIn("material_counting.unit", pending)
        self.assertIn("coupler_thread_qc.max_visible_threads_per_side", pending)
        self.assertNotIn("concrete_surface_qc.classes", pending)

    def test_write_rulebook_outputs_creates_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            paths = write_rulebook_outputs(output_dir, build_default_rulebook())

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            data = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(data["material_counting"]["unit"], "bar")
            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertIn("Field QC Rulebook", markdown)
            self.assertIn("Pending Confirmations", markdown)

    def test_rulebook_round_trip_from_json_dict(self):
        rulebook = build_default_rulebook()

        restored = FieldQcRulebook.from_dict(rulebook.to_dict())

        self.assertEqual(restored.material_counting.unit, "bar")
        self.assertEqual(restored.concrete_surface_qc.classes, CONCRETE_SURFACE_CLASSES)

    def test_cli_writes_default_rulebook_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            exit_code = rulebook_cli(["--output", str(output_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "field_qc_rulebook.json").exists())
            self.assertTrue((output_dir / "field_qc_rulebook.md").exists())

    def test_cli_file_path_execution_can_import_project_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path("scripts") / "build_field_qc_rulebook.py"),
                    "--output",
                    str(output_dir),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((output_dir / "field_qc_rulebook.json").exists())


if __name__ == "__main__":
    unittest.main()
