#!/usr/bin/env python3
"""用错误内容注入验证存档契约检查能拦住重复定义和缺失。"""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("archive", ROOT / "tools/check-archive-contract.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveContract(unittest.TestCase):
    def setUp(self):
        self.contract = archive.CONTRACT_PATH.read_text(encoding="utf-8")
        self.restore = (ROOT / "skills/dbs-restore/SKILL.md").read_text(encoding="utf-8")

    def test_current_files_pass(self):
        self.assertEqual(archive.check_contract(self.contract), [])
        self.assertEqual(archive.check_skill("dbs-restore", self.restore), [])

    def test_redefined_slug_rule_is_reported(self):
        errors = archive.check_skill("dbs-restore", self.restore + "\n默认项目名取自 `basename $(pwd)`。")
        self.assertTrue(any("项目名规则" in e for e in errors))

    def test_missing_link_is_reported(self):
        text = self.restore.replace("references/archive-contract.md", "")
        self.assertTrue(any("没有引用存档契约" in e for e in archive.check_skill("dbs-restore", text)))

    def test_missing_section_is_reported(self):
        errors = archive.check_contract(self.contract.replace("`## 待验证假设`", ""))
        self.assertTrue(any("待验证假设" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
