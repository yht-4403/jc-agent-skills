#!/usr/bin/env python3
"""用错误格式检查接手字段闸门。"""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("handoff", ROOT / "tools/check-skill-handoff.py")
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)

VALID = (
    "---\nname: sample\ndescription: test\nmetadata:\n  internal: true\n  dbs-handoff: |\n"
    "    - 方向未定 → 最多 4 个选题，停下等用户选定\n"
    "    - 方向已定 → 标题和开头\n"
    "    - 不交出：封面图片\n---\n正文\n"
)


class Handoff(unittest.TestCase):
    def test_valid_field(self):
        entries = handoff.read_handoff(VALID)
        self.assertEqual(len(entries), 3)
        self.assertEqual(handoff.check_entries(entries), [])

    def test_missing_field(self):
        self.assertIsNone(handoff.read_handoff("---\nname: sample\ndescription: test\n---\n"))

    def test_field_outside_metadata_is_ignored(self):
        text = "---\nname: sample\ndbs-handoff: |\n  - a → b\n---\n"
        self.assertIsNone(handoff.read_handoff(text))

    def test_missing_arrow(self):
        errors = handoff.check_entries(["- 方向未定，给选题", "- 不交出：图片"])
        self.assertTrue(any("→" in e for e in errors))

    def test_missing_or_misplaced_not_delivered(self):
        self.assertTrue(handoff.check_entries(["- a → b"]))
        errors = handoff.check_entries(["- 不交出：图片", "- a → b"])
        self.assertTrue(any("最后一行" in e for e in errors))

    def test_too_long(self):
        errors = handoff.check_entries(["- a → " + "字" * 600, "- 不交出：图片"])
        self.assertTrue(any("超过" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
