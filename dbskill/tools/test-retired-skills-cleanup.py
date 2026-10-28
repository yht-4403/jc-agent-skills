#!/usr/bin/env python3
"""验证已下线 Skill 清理脚本只处理可确认来自官方的副本。"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/dbs-update/scripts/cleanup_retired_skills.py"
RETIRED = json.loads((ROOT / "skills/dbs-update/references/retired-skills.json").read_text(encoding="utf-8"))


def official_content(name: str) -> bytes:
    """取该 Skill 在 Git 历史中最后一个存在的版本。"""
    path = f"skills/{name}/SKILL.md"
    for commit in subprocess.check_output(["git", "log", "--format=%H", "--", path], cwd=ROOT, text=True).split():
        try:
            return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            continue
    raise AssertionError(f"Git 历史中找不到 {path}")


class RetiredCleanup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        names = [entry["name"] for entry in RETIRED["skills"]]
        self.name, self.other_name = names[0], names[1]
        self.content = official_content(self.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cleanup(self, *extra):
        output = subprocess.check_output(
            [sys.executable, str(SCRIPT), "--home", str(self.home), *extra], text=True
        )
        return json.loads(output)

    def make_skill(self, path: Path, content: bytes):
        path.mkdir(parents=True)
        (path / "SKILL.md").write_bytes(content)

    def test_official_copies_are_cleaned_and_others_kept(self):
        official_copy = self.home / ".codex/skills" / self.name
        self.make_skill(official_copy, self.content.replace(b"\n", b"\r\n"))

        modified_copy = self.home / ".cursor/skills" / self.name
        self.make_skill(modified_copy, self.content + b"\n# my notes\n")

        source = Path(self.tmp.name) / "repo/skills" / self.name
        self.make_skill(source, self.content)
        (self.home / ".agents/skills").mkdir(parents=True)
        official_link = self.home / ".agents/skills" / self.name
        official_link.symlink_to(source)

        (self.home / ".claude/skills").mkdir(parents=True)
        dangling = self.home / ".claude/skills" / self.other_name
        dangling.symlink_to(Path(self.tmp.name) / "missing" / self.other_name)

        other_source = Path(self.tmp.name) / "mine" / self.other_name
        self.make_skill(other_source, b"---\nname: mine\n---\n")
        (self.home / ".kiro/skills").mkdir(parents=True)
        other_link = self.home / ".kiro/skills" / self.other_name
        other_link.symlink_to(other_source)

        grok_bridge = self.home / ".grok/skills" / self.name
        self.make_skill(grok_bridge, f"## Grok Bridge\n\n- Source of truth: {Path(self.tmp.name)}/gone/skills/{self.name}/SKILL.md\n".encode())

        planned = self.run_cleanup("--dry-run")
        self.assertTrue(official_copy.is_dir() and official_link.is_symlink() and dangling.is_symlink())
        self.assertEqual(len(planned["removed"]), 2)
        self.assertEqual(len(planned["backed_up"]), 2)
        self.assertEqual(len(planned["kept"]), 2)

        result = self.run_cleanup()
        self.assertFalse(official_copy.exists())
        self.assertFalse(os.path.lexists(official_link))
        self.assertTrue(source.is_dir(), "只移除链接，不碰链接目标")
        self.assertFalse(os.path.lexists(dangling))
        self.assertFalse(grok_bridge.exists())
        self.assertTrue(modified_copy.is_dir(), "改过的副本必须保留")
        self.assertTrue(other_link.is_symlink(), "指向其他内容的链接必须保留")
        backup_dir = Path(result["backup_dir"])
        self.assertTrue((backup_dir / "codex" / self.name / "SKILL.md").is_file())
        self.assertTrue((backup_dir / "grok" / self.name / "SKILL.md").is_file())

    def test_agent_dirs_match_install_skill(self):
        import re
        sys.path.insert(0, str(SCRIPT.parent))
        import cleanup_retired_skills
        installer = (ROOT / "skills/dbs-install-skill/scripts/install-skill.sh").read_text(encoding="utf-8")
        expected = set(re.findall(r'"\$INSTALL_HOME/(\.[a-z-]+)/skills"', installer))
        # Grok 使用适配层而非链接，清理脚本单独处理 .grok
        self.assertEqual(set(cleanup_retired_skills.AGENT_SKILL_DIRS) | {".grok"}, expected)

    def test_nothing_to_clean(self):
        result = self.run_cleanup()
        self.assertEqual((result["removed"], result["backed_up"], result["kept"]), ([], [], []))
        self.assertFalse((self.home / ".dbs").exists())


if __name__ == "__main__":
    unittest.main()
