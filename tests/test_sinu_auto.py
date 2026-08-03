"""Basic smoke tests for the SINU parser/config."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sinu_auto.config import load_settings  # noqa: E402
from sinu_auto.parser import Group, GroupParser  # noqa: E402


class TestConfig(unittest.TestCase):
    def test_load_settings_from_env(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("SINU_USERNAME=123\nSINU_PASSWORD=secret\n")
            settings = load_settings(env_path=str(env))
            self.assertEqual(settings.username, "123")
            self.assertEqual(settings.password, "secret")

    def test_missing_credentials_raises(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("# no creds here\n")
            with self.assertRaises(ValueError):
                load_settings(env_path=str(env))


class TestParser(unittest.TestCase):
    def test_to_json_shape(self):
        groups = [
            Group(grupo="PIG03", sin_cruce=True, cupo_disp=True, cupo_valor=1,
                  horario="Jueves 18:30 - 21:30", fecha="06/08/2026")
        ]
        data = json.loads(GroupParser.to_json(groups))
        self.assertEqual(data[0]["grupo"], "PIG03")
        self.assertTrue(data[0]["sin_cruce"])
        self.assertTrue(data[0]["cupo_disp"])


if __name__ == "__main__":
    unittest.main()
