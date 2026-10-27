#!/usr/bin/env python3

import json
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("manage.py")
MODULE_SPEC = importlib.util.spec_from_file_location("jc_skill_manager", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load Skill manager: {MODULE_PATH}")
manage = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(manage)


class ManageSkillChannelsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "active-skills.json"
        self.channels = self.root / "skill-channels.json"
        self.profiles = self.root / "skill-profiles.json"
        self.make_skill("resume", "resume", "旧版简历能力")
        self.make_skill("resume-v2", "resume-v2", "第二版简历能力")
        self.make_skill("resume-v3", "resume-v3", "简历优化与岗位匹配")
        self.make_skill("other", "other", "其他常用能力")
        self.channels.write_text(
            json.dumps(
                {
                    "version": 1,
                    "channels": [
                        {
                            "family": "resume",
                            "latest": "v3",
                            "versions": {
                                "v1": "resume",
                                "v2": "resume-v2",
                                "v3": "resume-v3",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.profiles.write_text(
            json.dumps(
                {
                    "version": 1,
                    "profiles": [
                        {
                            "name": "default",
                            "skills": ["other"],
                            "channels": ["resume"],
                            "require_all_prefixes": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_skill(self, relative: str, name: str, description: str) -> None:
        directory = self.root / relative
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
            encoding="utf-8",
        )

    def test_select_latest_keeps_history_but_only_activates_latest(self) -> None:
        manage.save_manifest(
            self.manifest,
            {
                "resume": "resume",
                "resume-v2": "resume-v2",
                "resume-v3": "resume-v3",
                "other": "other",
            },
        )

        family, version, declared_name = manage.select_latest(
            self.root, self.manifest, self.channels, "resume"
        )

        self.assertEqual((family, version, declared_name), ("resume", "v3", "resume-v3"))
        self.assertEqual(
            manage.manifest_entries(self.manifest),
            {"other": "other", "resume-v3": "resume-v3"},
        )
        self.assertTrue((self.root / "resume" / "SKILL.md").is_file())
        self.assertTrue((self.root / "resume-v2" / "SKILL.md").is_file())

    def test_promote_moves_channel_without_rewriting_old_versions(self) -> None:
        manage.save_manifest(self.manifest, {"resume-v3": "resume-v3"})

        manage.promote_latest(self.root, self.manifest, self.channels, "resume", "v2")

        self.assertEqual(manage.load_channels(self.channels)["resume"]["latest"], "v2")
        self.assertEqual(manage.manifest_entries(self.manifest), {"resume-v2": "resume-v2"})
        self.assertTrue((self.root / "resume-v3" / "SKILL.md").is_file())

    def test_audit_reports_multiple_active_versions(self) -> None:
        manage.save_manifest(
            self.manifest,
            {"resume-v2": "resume-v2", "resume-v3": "resume-v3"},
        )

        self.assertEqual(
            manage.channel_issues(self.root, self.manifest, self.channels),
            ["MULTIPLE_ACTIVE_VERSIONS resume: v2, v3"],
        )

    def test_search_finds_inactive_skill_without_activating_it(self) -> None:
        manage.save_manifest(self.manifest, {"other": "other"})

        records = manage.search_catalog(self.root, self.manifest, "简历优化")

        self.assertEqual(records[0]["path"], "resume-v3")
        self.assertFalse(records[0]["active"])
        self.assertEqual(manage.manifest_entries(self.manifest), {"other": "other"})

    def test_search_splits_compound_chinese_query_into_bigrams(self) -> None:
        manage.save_manifest(self.manifest, {"other": "other"})
        self.make_skill("split-match", "split-match", "负责简历诊断，并优化岗位表达")

        records = manage.search_catalog(self.root, self.manifest, "简历优化")

        self.assertIn("split-match", [record["path"] for record in records])

    def test_profile_follows_latest_channel_without_parallel_versions(self) -> None:
        desired = manage.resolve_profile(
            self.root, self.channels, self.profiles, "default"
        )

        self.assertEqual(desired, {"other": "other", "resume-v3": "resume-v3"})

    def test_profile_rejects_missing_required_brand_skill(self) -> None:
        self.make_skill("jc-new", "jc-new", "新的 JC 能力")
        data = json.loads(self.profiles.read_text(encoding="utf-8"))
        data["profiles"][0]["require_all_prefixes"] = ["jc-"]
        self.profiles.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "omits required Skills: jc-new"):
            manage.resolve_profile(self.root, self.channels, self.profiles, "default")


class KimiSyncTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/'source';self.root.mkdir();self.rt=self.base/'runtime';self.rt.mkdir();self.man=self.base/'manifest.json'
  for name in ['one','two']:
   p=self.root/name;p.mkdir();(p/'SKILL.md').write_text(f'---\nname: {name}\ndescription: test\n---\n')
  manage.save_manifest(self.man,{'one':'one','two':'two'})
 def test_reconcile_and_preserve(self):
  native=self.rt/'native';native.mkdir();external=self.base/'external';external.mkdir();(self.rt/'unrelated').symlink_to(external)
  self.assertEqual(manage.sync_kimi_work(self.root,self.man,self.rt,True),(2,0));self.assertFalse((self.rt/'one').exists())
  self.assertEqual(manage.sync_kimi_work(self.root,self.man,self.rt),(2,0));self.assertEqual(manage.sync_kimi_work(self.root,self.man,self.rt),(2,0))
  manage.save_manifest(self.man,{'two':'two'});self.assertEqual(manage.sync_kimi_work(self.root,self.man,self.rt),(1,1));self.assertTrue(native.exists());self.assertTrue((self.rt/'unrelated').is_symlink());self.assertFalse((self.rt/'one').exists())
 def test_conflict_preflight(self):
  (self.rt/'two').mkdir()
  with self.assertRaises(ValueError):manage.sync_kimi_work(self.root,self.man,self.rt)
  self.assertFalse((self.rt/'one').exists())
 def test_modified_link_refused(self):
  manage.sync_kimi_work(self.root,self.man,self.rt);(self.rt/'one'/'SKILL.md').unlink();(self.rt/'one'/'SKILL.md').symlink_to(self.root/'two'/'SKILL.md')
  manage.save_manifest(self.man,{'two':'two'})
  with self.assertRaises(ValueError):manage.sync_kimi_work(self.root,self.man,self.rt)
  self.assertTrue((self.rt/'one').exists())
 def test_broken_owned_link_removed(self):
  manage.sync_kimi_work(self.root,self.man,self.rt);(self.root/'one'/'SKILL.md').unlink();(self.root/'one').rmdir();manage.save_manifest(self.man,{'two':'two'})
  self.assertEqual(manage.sync_kimi_work(self.root,self.man,self.rt),(1,1))

class MultiRuntimeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / "source"
        self.root.mkdir()
        self.manifest = self.root / "active.json"
        for name in ("one", "two"):
            path = self.root / name
            path.mkdir()
            (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")
        manage.save_manifest(self.manifest, {"one": "one", "two": "two"})

    def test_flat_conflict_is_refused_before_stale_link_removal(self):
        runtime = self.home / "runtime"
        runtime.mkdir()
        (runtime / "old").symlink_to(self.root / "one")
        (runtime / "two").mkdir()
        with self.assertRaises(ValueError):
            manage.sync_flat_runtime(self.root, self.manifest, runtime)
        self.assertTrue((runtime / "old").is_symlink())
        self.assertFalse((runtime / "one").exists())

    def test_workbuddy_uses_its_own_root_and_dry_run_does_not_write(self):
        (self.home / ".workbuddy").mkdir()
        with patch.object(manage.Path, "home", return_value=self.home):
            self.assertEqual(manage.sync_workbuddy(self.root, self.manifest, True), (2, 0))
            self.assertFalse((self.home / ".workbuddy/skills").exists())
            manage.sync_workbuddy(self.root, self.manifest)
            self.assertEqual(manage.audit_flat_runtime(self.root, self.manifest,
                                                       self.home / ".workbuddy/skills"), [])
            self.assertFalse((self.home / ".codebuddy").exists())

    def test_kimi_code_uses_verified_desktop_root_without_legacy_fallback(self):
        (self.home / '.kimi-code').mkdir()
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.dict(manage.os.environ, {}, clear=True):
            self.assertEqual(manage.sync_kimi_code(self.root, self.manifest, True), (2, 0))
            self.assertFalse((self.home / '.kimi-code/skills').exists())
            manage.sync_kimi_code(self.root, self.manifest)
            self.assertEqual(manage.audit_flat_runtime(self.root, self.manifest,
                                                       self.home / '.kimi-code/skills'), [])
            self.assertFalse((self.home / '.agents/skills').exists())
            self.assertFalse((self.home / '.kimi/skills').exists())

    def test_unregistered_real_skill_is_reported_and_preserved(self):
        runtime = self.home / "runtime"
        manage.sync_flat_runtime(self.root, self.manifest, runtime)
        extra = runtime / "extra"
        extra.mkdir()
        (extra / "SKILL.md").write_text("custom content")
        with patch.object(manage, "platform_owned", return_value=set()):
            self.assertEqual(manage.audit_flat_runtime(self.root, self.manifest, runtime),
                             [f"UNMANAGED_REAL_SKILL {extra}"])
        self.assertEqual((extra / "SKILL.md").read_text(), "custom content")

    def test_toml_edit_preserves_unrelated_settings_and_multiline_arrays(self):
        text = '# Keep\n[cli]\nmodel = "existing"\n[skills]\npaths = [\n "~/old", # note\n]\nother = true\n[ui]\ntheme = "dark"\n'
        changed = manage.update_toml_arrays(text, "skills", {"paths": ["~/new"], "ignore": []})
        data = manage.tomllib.loads(changed)
        self.assertEqual(data['cli'], {'model': 'existing'})
        self.assertEqual(data['ui'], {'theme': 'dark'})
        self.assertEqual(data['skills'], {'paths': ['~/new'], 'ignore': [], 'other': True})
        self.assertTrue(changed.startswith('# Keep\n'))

    def test_grok_reconcile_preserves_user_paths_and_removes_only_owned_paths(self):
        runtime = self.home / '.grok'
        runtime.mkdir()
        config = runtime / 'config.toml'
        config.write_text('[cli]\nmodel = "keep"\n[skills]\npaths = ["~/user"]\n')
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'grok_binary', return_value=Path('/mock/grok')), \
             patch.object(manage, 'grok_managed_config', return_value={'paths': [str(self.root/'one')], 'ignore': []}):
            original = config.read_text()
            manage.sync_grok(self.root, self.manifest, True)
            self.assertEqual(config.read_text(), original)
            manage.sync_grok(self.root, self.manifest)
            with patch.object(manage, 'grok_managed_config', return_value={'paths': [], 'ignore': []}):
                manage.sync_grok(self.root, self.manifest)
        self.assertEqual(manage.tomllib.loads(config.read_text())['skills']['paths'], ['~/user'])
        self.assertEqual(manage.tomllib.loads(config.read_text())['cli']['model'], 'keep')

    def test_grok_audit_checks_actual_sources_and_duplicate_names(self):
        data = {'skills': [{'name':'one','source':{'path':str(self.root/'one/SKILL.md')}},
                           {'name':'one','source':{'path':'/plugin/one/SKILL.md'}}],
                'externalCompat':{'cells':[{'vendor':'claude','surface':'skills','enabled':True}]}}
        process = manage.subprocess.CompletedProcess([], 0, json.dumps(data), '')
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'grok_binary', return_value=Path('/mock/grok')), \
             patch.object(manage, 'grok_managed_config', return_value={'paths': [], 'ignore': []}), \
             patch.object(manage.subprocess, 'run', return_value=process):
            issues = manage.audit_grok(self.root, self.manifest)
        self.assertIn(f'MISSING_GROK_SOURCE two: {(self.root / "two").resolve()}', issues)
        self.assertIn('DUPLICATE_GROK_SKILL_NAME one: 2 providers', issues)

    def test_grok_registered_qualifiers_require_canonical_personal_source(self):
        providers = [{'name': 'one', 'invocableAs': 'user:one',
                      'source': {'path': str(self.root/'one/SKILL.md')}},
                     {'name': 'one', 'invocableAs': 'plugin:one',
                      'source': {'path': '/plugin/one/SKILL.md'}},
                     {'name': 'two', 'source': {'path':str(self.root/'two/SKILL.md')}}]
        data = {'skills':providers, 'externalCompat':{'cells':[{'vendor':'claude','surface':'skills','enabled':True}]},
                'projectInstructions':[{'scope':'global','path':str(self.home/'.claude/CLAUDE.md')}]}
        policy = {'grok':{'namespaced_providers':{'one':{
            'preferred_invocation':'user:one','allowed_invocations':['user:one','plugin:one']}}}}
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'grok_binary', return_value=Path('/mock/grok')), \
             patch.object(manage, 'runtime_policy', return_value=policy), \
             patch.object(manage, 'grok_managed_config', return_value={'paths': [], 'ignore': []}), \
             patch.object(manage.subprocess, 'run', return_value=manage.subprocess.CompletedProcess([],0,json.dumps(data),'')):
            self.assertEqual(manage.audit_grok(self.root, self.manifest), [])
            providers[0]['source']['path'] = '/wrong/one/SKILL.md'
            with patch.object(manage.subprocess, 'run', return_value=manage.subprocess.CompletedProcess([],0,json.dumps(data),'')):
                self.assertIn('WRONG_GROK_PREFERRED_PROVIDER one: user:one', manage.audit_grok(self.root, self.manifest))

    def test_multiline_description_is_searchable(self):
        skill = self.root / 'one/SKILL.md'
        skill.write_text('---\nname: one\ndescription: >-\n  中文能力第一行\n  English second line\nversion: 1\n---\n')
        self.assertEqual(manage.frontmatter(skill.parent), ('one', '中文能力第一行 English second line'))
        records = manage.search_catalog(self.root, self.manifest, '中文能力')
        self.assertEqual(records[0]['name'], 'one')

    def test_rules_cover_native_client_homes_and_preserve_user_text(self):
        for name in ['.codebuddy', '.workbuddy', '.dsh', '.kimi-code']:
            (self.home/name).mkdir()
        rule = self.home/'.dsh/AGENTS.md'
        rule.write_text('User preference before.\n')
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'kimi_work_runtime_dir', return_value=None):
            manage.sync_managed_rules(self.root)
            self.assertEqual(manage.audit_managed_rules(self.root), [])
            self.assertIn('User preference before.', rule.read_text())
            self.assertIn(' update <仓库相对路径>',rule.read_text())
            self.assertTrue((self.home/'.codebuddy/CODEBUDDY.md').is_file())
            self.assertTrue((self.home/'.workbuddy/CODEBUDDY.md').is_file())
            self.assertTrue((self.home/'.kimi-code/AGENTS.md').is_file())
            rule.write_text(rule.read_text().replace('完成后必须执行', 'wrong rule'))
            self.assertIn(f'OUTDATED_MANAGED_RULE {rule}', manage.audit_managed_rules(self.root))

    def test_rules_use_configured_kimi_workdir_instead_of_guessed_global_file(self):
        runtime=self.home/'work/daimon/skills';runtime.mkdir(parents=True)
        workspace=self.home/'workspace';workspace.mkdir()
        (runtime.parent/'config.json').write_text(json.dumps({'agents':{'entries':{
            'main':{'workDir':str(workspace)}}}}))
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'kimi_work_runtime_dir', return_value=runtime):
            manage.sync_managed_rules(self.root)
            self.assertEqual(manage.audit_managed_rules(self.root), [])
            self.assertIn(('kimi-work',workspace/'AGENTS.md'),manage.managed_rule_targets())
            self.assertFalse((runtime.parent/'AGENTS.md').exists())

    def test_malformed_rule_aborts_before_any_rule_is_written(self):
        target=self.home/'.claude/CLAUDE.md';target.parent.mkdir()
        target.write_text(manage.MANAGED_START+' broken')
        with patch.object(manage.Path, 'home', return_value=self.home), \
             patch.object(manage, 'kimi_work_runtime_dir', return_value=None):
            with self.assertRaisesRegex(ValueError,'Malformed managed rule'):
                manage.sync_managed_rules(self.root)
        self.assertFalse((self.home/'.codex/AGENTS.md').exists())

    def test_update_refuses_source_escape_and_archived_version(self):
        channels=self.root/'channels.json'
        channels.write_text(json.dumps({'version':1,'channels':[{'family':'one','latest':'latest',
            'versions':{'latest':'one','v1':'two'}}]}))
        self.assertEqual(manage.complete_update(self.root,self.manifest,'one',channels),'one')
        with self.assertRaisesRegex(ValueError,'archived'):
            manage.complete_update(self.root,self.manifest,'two',channels)
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            manage.complete_update(self.root,self.manifest,'../',channels)

    def test_required_manager_cannot_be_deactivated(self):
        with self.assertRaisesRegex(ValueError,'Cannot deactivate'):
            manage.deactivate(self.root,self.manifest,'jc-skill-installer')

    def test_reconciliation_failure_cannot_be_reported_as_success(self):
        with patch.object(manage,'sync_default_flat_runtimes',return_value=()), \
             patch.object(manage,'audit',return_value=['WRONG_LINK test']):
            with self.assertRaisesRegex(ValueError,'verification failed'):
                manage.sync_and_check(self.root,self.manifest)

    def test_source_routes_are_preserved_and_restored_after_upstream_replacement(self):
        manager_dir=self.root/'jc-skill-installer';manager_dir.mkdir()
        native=self.root/'native/scripts';native.mkdir(parents=True)
        script=native/'install.sh';original='#!/usr/bin/env bash\nprintf "legacy body\\n"\n'
        script.write_text(original)
        policy={'management_routes':[{'path':'one'}],
                'management_script_routes':[{'path':'native/scripts/install.sh'}]}
        (manager_dir/'runtime-policy.json').write_text(json.dumps(policy))
        markdown=self.root/'one/SKILL.md';old=markdown.read_text()
        manage.sync_source_routes(self.root)
        self.assertEqual(manage.source_route_issues(self.root),[])
        self.assertIn('name: one',markdown.read_text())
        self.assertTrue(script.read_text().endswith(original.split('\n',1)[1]))
        markdown.write_text(old.replace('description: test','description: newer upstream'))
        script.write_text(original)
        self.assertTrue(manage.source_route_issues(self.root))
        manage.sync_source_routes(self.root)
        self.assertEqual(manage.source_route_issues(self.root),[])
        self.assertIn('newer upstream',markdown.read_text())

    def test_dbs_shell_bridge_runs_manager_before_any_legacy_mutation(self):
        manager_dir=self.root/'jc-skill-installer/scripts';manager_dir.mkdir(parents=True)
        (manager_dir/'manage.py').write_text('import sys\nprint("routed", " ".join(sys.argv[1:]))\n')
        script=self.root/'native/scripts/install.sh';script.parent.mkdir(parents=True)
        script.write_text('#!/usr/bin/env bash\n'+manage.script_route_block()+'\nprintf "LEGACY-WOULD-WRITE\\n"\n')
        result=manage.subprocess.run(['bash',str(script),'link','one'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('routed dbs-route link one',result.stdout)
        self.assertNotIn('LEGACY-WOULD-WRITE',result.stdout)

    def test_dbs_bridge_refuses_external_candidates_without_copying_or_linking(self):
        self.assertEqual(manage.resolve_dbs_source(self.root,'one'),(self.root/'one').resolve())
        external=self.home/'external';external.mkdir()
        with self.assertRaisesRegex(ValueError,'import the candidate'):
            manage.resolve_dbs_source(self.root,str(external))
        self.assertFalse((self.root/'external').exists())
        self.assertFalse((self.home/'.agents/skills').exists())


if __name__ == "__main__":
    unittest.main()
