#!/usr/bin/env python3
"""用错误指令注入检查路由静态闸门；不把静态检查当成行为测试。"""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("routing", ROOT / "tools/check-skill-routing-contract.py")
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


class RoutingContract(unittest.TestCase):
    def setUp(self):
        self.entry = (ROOT / "skills/dbs/SKILL.md").read_text(encoding="utf-8")
        self.composition = (ROOT / "skills/dbs/references/composition-contract.md").read_text(encoding="utf-8")

    def test_current_contract(self):
        self.assertEqual(routing.check_entry_contract(self.entry, self.composition), [])

    def test_global_execution_ban_reintroduced(self):
        errors = routing.check_entry_contract(self.entry + "\n本轮不得执行入选 Skill 的业务流程。", self.composition)
        self.assertTrue(any("已废弃" in e and "本轮不得执行" in e for e in errors))

    def test_pause_hidden_in_reference(self):
        errors = routing.check_entry_contract(self.entry, self.composition + "\n输出推荐和组合提示词后立即结束。")
        self.assertTrue(any("composition-contract.md" in e and "已废弃" in e for e in errors))

    def test_forced_consensus_in_reference(self):
        errors = routing.check_entry_contract(self.entry, self.composition + "\n最终只交付一份由主 Skill 统领的结果。")
        self.assertTrue(any("已废弃" in e for e in errors))

    def test_portable_prompt_is_allowed(self):
        entry = self.entry + "\n用户只需要可复制提示词时，交付提示词后停止。"
        self.assertEqual(routing.check_entry_contract(entry, self.composition), [])


class LeafMentions(unittest.TestCase):
    NAMES = ["dbs", "dbs-content", "dbs-content-value", "dbs-save", "dbs-restore"]

    def test_leaf_naming_another_leaf_is_reported(self):
        found = routing.find_leaf_mentions("dbs-content", "需要评估时用 `dbs-content-value`。", self.NAMES)
        self.assertEqual(found, [(1, "dbs-content-value")])

    def test_self_hub_and_prefix_are_ignored(self):
        text = "本 Skill 是 dbs-content，可以输入 `/dbs`，存档在 ~/.dbs/ 下。"
        self.assertEqual(routing.find_leaf_mentions("dbs-content", text, self.NAMES), [])

    def test_allowed_dependency_is_ignored(self):
        self.assertEqual(routing.find_leaf_mentions("dbs-restore", "恢复 dbs-save 的存档。", self.NAMES), [])
        self.assertEqual(routing.find_leaf_mentions("dbs-restore", "再用 dbs-content 写。", self.NAMES), [(1, "dbs-content")])


if __name__ == "__main__":
    unittest.main()
