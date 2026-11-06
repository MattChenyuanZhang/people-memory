import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from people_match.setup_skills import install_skills


class SetupSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"CODEX_HOME": str(self.home / ".codex"), "CLAUDE_CONFIG_DIR": str(self.home / ".claude")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_detected_hosts_and_repeat_install(self):
        (self.home / ".codex").mkdir()
        (self.home / ".claude").mkdir()
        result = install_skills(home=self.home)
        self.assertEqual(len(result["skills"]), 4)
        self.assertTrue(all(row["status"] == "installed" for row in result["skills"]))
        self.assertTrue((self.home / ".codex/skills/record/agents/openai.yaml").is_file())
        self.assertTrue(all(row["status"] == "already_installed" for row in install_skills(home=self.home)["skills"]))

    def test_custom_skill_is_preserved(self):
        target = self.home / ".codex/skills/record"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("My own record command")
        result = install_skills(home=self.home)
        self.assertEqual(result["skills"][1]["status"], "skipped")
        self.assertEqual((target / "SKILL.md").read_text(), "My own record command")
        self.assertFalse((target / "agents").exists())

    def test_no_app_does_not_create_host_directories(self):
        self.assertEqual(install_skills(home=self.home)["skills"], [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_explicit_host_can_be_installed_before_first_launch(self):
        result = install_skills("claude-code", home=self.home)
        self.assertEqual(len(result["skills"]), 2)
        self.assertTrue((self.home / ".claude/skills/record/SKILL.md").is_file())
        self.assertFalse((self.home / ".codex").exists())

    def test_codex_default_discovery_directory(self):
        (self.home / ".codex").mkdir()
        with patch.dict(os.environ):
            os.environ.pop("CODEX_HOME", None)
            install_skills(home=self.home)
        self.assertTrue((self.home / ".agents/skills/record/SKILL.md").is_file())

    def test_cli_init_installs_and_opt_out_preserves_choice(self):
        (self.home / ".codex").mkdir()
        command = [sys.executable, "-m", "people_match.cli", "--db", str(self.home / "memory.sqlite3"), "init"]
        result = subprocess.run(command + ["--no-skills"], capture_output=True, text=True, check=True)
        self.assertNotIn("skills", json.loads(result.stdout))
        self.assertFalse((self.home / ".codex/skills").exists())
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(len(json.loads(result.stdout)["skills"]), 2)
        self.assertTrue((self.home / ".codex/skills/record/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
