#!/usr/bin/env python3
"""Test catalog discovery without asking a model to memorize expected routes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discovery', ROOT / 'skills/dbs/scripts/list-official-skills.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Discovery(unittest.TestCase):
    def test_snapshot_and_project_catalog_match(self):
        skill = ROOT / 'skills/dbs'
        self.assertEqual([x['name'] for x in m.load_catalog(skill, ROOT) if x['name'] != 'dbs'],
                         [x['name'] for x in m.load_catalog(skill, None)])

    def test_navigation_and_neighbors_are_distinct(self):
        descriptions = {x['name']: x['description'] for x in m.load_catalog(ROOT / 'skills/dbs', ROOT)}
        for name in ('dbs-video-navigation', 'dbs-video-extract', 'dbs-title-cover-intro', 'dbs-content-risk-check'):
            actual = m.read_frontmatter_description(ROOT / 'skills' / name / 'SKILL.md')
            self.assertEqual(actual, descriptions[name])
        self.assertEqual(len({descriptions[n] for n in ('dbs-video-navigation', 'dbs-video-extract', 'dbs-title-cover-intro')}), 3)

    def test_missing_broken_and_conflicting_installations(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            roots = [root/'one', root/'two']
            self.assertIsNone(m.locate_installed_skill('sample', roots))
            for r in roots:
                (r/'sample').mkdir(parents=True)
                (r/'sample/SKILL.md').write_text('---\nname: sample\ndescription: test\n---\n')
            self.assertEqual(m.locate_installed_skill('sample', roots), (roots[0]/'sample').resolve())
            (roots[1]/'sample/SKILL.md').write_text('---\nname: sample\ndescription: changed\n---\n')
            self.assertEqual(m.locate_installed_skill('sample', roots), (roots[0]/'sample').resolve())
            (roots[0]/'sample/SKILL.md').write_text('---\nname: other\ndescription: test\n---\n')
            self.assertEqual(m.locate_installed_skill('sample', roots), (roots[1]/'sample').resolve())

    def test_handoff_field(self):
        handoff = m.read_frontmatter_handoff(ROOT/'skills/dbs-title-cover-intro/SKILL.md')
        self.assertIn('→', handoff)
        self.assertTrue(handoff.splitlines()[-1].startswith('- 不交出：'))
        self.assertEqual(m.read_frontmatter_handoff(ROOT/'skills/dbs/SKILL.md'), '')

    def test_multiline_description(self):
        self.assertIn('理论溯源', m.read_frontmatter_description(ROOT/'skills/dbs-theory-grounding/SKILL.md'))

if __name__ == '__main__':
    unittest.main()
