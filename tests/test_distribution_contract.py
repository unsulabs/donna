import ast
import json
import re
import unittest
from pathlib import Path
from support import ROOT
from donna_runtime import __version__, models
from donna_runtime.cli import parser

class DistributionContract(unittest.TestCase):
    def test_version_consistency(self):
        self.assertIn('version: '+__version__,(ROOT/'distribution.yaml').read_text())
        self.assertIn(__version__,(ROOT/'README.md').read_text())

    def test_six_skills_present_and_named(self):
        names={'donna-session','donna-planning','donna-team-orchestration','donna-operational-review','donna-team-development','donna-setup'}
        for name in names:
            content=(ROOT/'skills'/name/'SKILL.md').read_text()
            self.assertTrue(content.startswith('---\n'))
            self.assertIn('name: '+name,content)
            self.assertIn('version: '+__version__,content)
            self.assertGreater(len(content),1800)

    def test_starter_team_has_no_fabricated_profiles(self):
        value=json.loads((ROOT/'.team.example').read_text())
        self.assertEqual(value,{'schema_version':2,'members':[]})

    def test_sample_plan_is_valid_and_has_all_roles(self):
        value=models.plan(json.loads((ROOT/'examples/plan.json').read_text()))
        self.assertEqual({t['owner']['kind'] for t in value['tasks']},{'user','agent','donna'})

    def test_sample_member_is_not_ready(self):
        value=models.member(json.loads((ROOT/'examples/member.json').read_text()))
        self.assertEqual(value['status'],'proposed')

    def test_live_tests_not_falsely_marked_pass(self):
        value=json.loads((ROOT/'examples/live-acceptance.json').read_text())
        self.assertEqual(len(value['tests']),18)
        self.assertEqual({t['status'] for t in value['tests']},{'NOT_RUN'})

    def test_soul_bootstraps_active_profile(self):
        content=(ROOT/'SOUL.md').read_text()
        self.assertIn('donna-session',content)
        self.assertIn('$HERMES_HOME',content)
        self.assertLess(len(content),18000)

    def test_no_runtime_data_distribution_owned(self):
        content=(ROOT/'distribution.yaml').read_text().split('distribution_owned:',1)[1]
        for path in ('  - memories/','  - .team\n','  - donna-state/','  - .env\n','  - donna-ops.json'):
            self.assertNotIn(path,content)

    def test_fresh_defaults_do_not_blanket_allow_scripts(self):
        content=(ROOT/'config.yaml').read_text()
        self.assertIn('command_allowlist: []',content)
        self.assertIn('dispatch_in_gateway: false',content)
        self.assertNotIn('model:\n',content)

    def test_readme_local_links_exist(self):
        content=(ROOT/'README.md').read_text()
        for relative in re.findall(r'\]\((docs/[^)]+)\)',content):
            self.assertTrue((ROOT/relative).is_file(),relative)

    def test_python_310_grammar(self):
        for path in (ROOT/'scripts').rglob('*.py'):
            ast.parse(path.read_text(),filename=str(path),feature_version=(3,10))

    def test_cli_reference_generated_matches(self):
        content=(ROOT/'docs/CLI.md').read_text()
        import argparse
        for action in parser()._actions:
            if isinstance(action,argparse._SubParsersAction):
                for name in action.choices:self.assertIn(name,content)
