"""Tests for the SINU parser, config, filters, login, and CLI helpers."""
import json
import tempfile
from pathlib import Path

import pytest

from sinu_auto.cli import filter_candidates
from sinu_auto.config import SinusSettings, load_settings
from sinu_auto.login import LoginError, login, set_input
from sinu_auto.parser import Group, GroupParser


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_load_settings_from_env(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("SINU_USERNAME=123\nSINU_PASSWORD=secret\n")
            settings = load_settings(env_path=str(env))
            assert settings.username == "123"
            assert settings.password == "secret"

    def test_missing_credentials_raises(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("# no creds here\n")
            with pytest.raises(ValueError):
                load_settings(env_path=str(env))

    def test_yaml_settings_are_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / ".env"
            env.write_text("SINU_USERNAME=u\nSINU_PASSWORD=p\n")
            cfg = td / "settings.yaml"
            cfg.write_text(
                "sinu:\n"
                "  url: 'https://example.test/sinugwt/'\n"
                "target:\n"
                "  course_code: 'ABC12'\n"
                "  group_prefix: 'PG'\n"
                "  require_no_conflict: false\n"
                "  fixed_schedule:\n"
                "    - name: 'CALCULO'\n"
                "      days: ['Lunes']\n"
                "      time: '08:00-10:00'\n"
                "enroll:\n"
                "  auto: false\n"
                "  max_attempts: 5\n"
                "  wait_between_checks: 60\n"
            )
            s = load_settings(str(cfg), str(env))
            assert s.url == "https://example.test/sinugwt/"
            assert s.course_code == "ABC12"
            assert s.group_prefix == "PG"
            assert s.require_no_conflict is False
            assert s.fixed_schedule == [{"name": "CALCULO", "days": ["Lunes"], "time": "08:00-10:00"}]
            assert s.auto_enroll is False
            assert s.max_attempts == 5
            assert s.watch_interval == 60

    def test_env_file_overrides_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / ".env"
            env.write_text("SINU_USERNAME=u\nSINU_PASSWORD=p\nSINU_URL=https://env.test/\n")
            cfg = td / "settings.yaml"
            cfg.write_text("sinu:\n  url: 'https://yaml.test/'\n")
            s = load_settings(str(cfg), str(env))
            assert s.url == "https://env.test/"

    def test_os_env_overrides_env_file(self, monkeypatch):
        monkeypatch.setenv("SINU_USERNAME", "osuser")
        monkeypatch.setenv("SINU_PASSWORD", "ospass")
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("SINU_USERNAME=fileuser\nSINU_PASSWORD=filepass\n")
            s = load_settings(env_path=str(env))
            assert s.username == "osuser"
            assert s.password == "ospass"

    def test_invalid_max_attempts_raises(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / ".env"
            env.write_text("SINU_USERNAME=u\nSINU_PASSWORD=p\n")
            cfg = td / "settings.yaml"
            cfg.write_text("enroll:\n  max_attempts: 0\n")
            with pytest.raises(ValueError, match="max_attempts"):
                load_settings(str(cfg), str(env))

    def test_negative_watch_interval_raises(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / ".env"
            env.write_text("SINU_USERNAME=u\nSINU_PASSWORD=p\n")
            cfg = td / "settings.yaml"
            cfg.write_text("enroll:\n  wait_between_checks: -5\n")
            with pytest.raises(ValueError, match="wait_between_checks"):
                load_settings(str(cfg), str(env))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class FakePage:
    """Minimal stand-in for playwright.Page — returns canned table rows."""

    def __init__(self, rows):
        self._rows = rows

    def evaluate(self, script, arg=None):
        return self._rows


def _cell(txt="", imgs=None):
    return {"txt": txt, "imgs": imgs or []}


def _full_row(grupo="PIG03", cruce_img="false_cruce.png", cupo="5",
              horario="Jueves 18:30 - 21:30", fecha="06/08/2026"):
    cells = [_cell(imgs=[cruce_img]), _cell(txt=cupo)]
    # pad with empty cells up to index 10 (horario/fecha positions)
    while len(cells) < 11:
        cells.append(_cell())
    cells[0]["txt"] = grupo
    cells[9]["txt"] = horario
    cells[10]["txt"] = fecha
    return cells


class TestParser:
    def test_to_json_shape(self):
        groups = [
            Group(grupo="PIG03", sin_cruce=True, cupo_disp=True, cupo_valor=1,
                  horario="Jueves 18:30 - 21:30", fecha="06/08/2026")
        ]
        data = json.loads(GroupParser.to_json(groups))
        assert data[0]["grupo"] == "PIG03"
        assert data[0]["sin_cruce"] is True
        assert data[0]["cupo_disp"] is True
        assert data[0]["cupo_valor"] == 1

    def test_group_to_dict(self):
        g = Group(grupo="PIG02", sin_cruce=False, cupo_disp=True, cupo_valor=17,
                  horario="Martes 18:30 - 21:30", fecha="06/08/2026",
                  raw_cruce="true_cruce.png", raw_cupo="17")
        d = g.to_dict()
        assert d == {
            "grupo": "PIG02",
            "sin_cruce": False,
            "cupo_disp": True,
            "cupo_valor": 17,
            "horario": "Martes 18:30 - 21:30",
            "fecha": "06/08/2026",
        }

    def test_parse_available_group(self):
        page = FakePage([_full_row(grupo="PIG03", cruce_img="false_cruce.png", cupo="5")])
        groups = GroupParser().parse(page, group_prefix="PIG")
        assert len(groups) == 1
        g = groups[0]
        assert g.grupo == "PIG03"
        assert g.sin_cruce is True
        assert g.cupo_disp is True
        assert g.cupo_valor == 5
        assert g.horario == "Jueves 18:30 - 21:30"
        assert g.fecha == "06/08/2026"

    def test_parse_full_group_icon(self):
        # Icon in cupo cell (true_cruce.png) = no capacity
        page = FakePage([_full_row(grupo="PIG01", cruce_img="false_cruce.png", cupo="true_cruce.png")])
        groups = GroupParser().parse(page, group_prefix="PIG")
        assert len(groups) == 1
        assert groups[0].cupo_disp is False
        assert groups[0].cupo_valor == 0

    def test_parse_conflict_group(self):
        page = FakePage([_full_row(grupo="PIG02", cruce_img="true_cruce.png", cupo="3")])
        groups = GroupParser().parse(page, group_prefix="PIG")
        assert groups[0].sin_cruce is False

    def test_parse_skips_rows_without_group_code(self):
        # Row mentions prefix but has no PIGxx code — should be skipped
        junk = [_cell(txt="PIGMENTO"), _cell(txt="x")] + [_cell() for _ in range(9)]
        good = _full_row(grupo="PIG07", cruce_img="false_cruce.png", cupo="1")
        groups = GroupParser().parse(FakePage([junk, good]), group_prefix="PIG")
        assert [g.grupo for g in groups] == ["PIG07"]

    def test_parse_skips_short_rows(self):
        page = FakePage([[_cell(txt="PIG01")], [_cell(txt="PIG02"), _cell(txt="x")]])
        assert GroupParser().parse(page, group_prefix="PIG") == []

    def test_parse_multiple_groups(self):
        page = FakePage([
            _full_row(grupo="PIG01", cruce_img="false_cruce.png", cupo="0"),
            _full_row(grupo="PIG02", cruce_img="false_cruce.png", cupo="2"),
        ])
        groups = GroupParser().parse(page, group_prefix="PIG")
        assert [g.grupo for g in groups] == ["PIG01", "PIG02"]
        assert [g.cupo_disp for g in groups] == [False, True]


# ---------------------------------------------------------------------------
# Candidate filtering
# ---------------------------------------------------------------------------

def _group(grupo="PIG03", sin_cruce=True, cupo_disp=True, cupo_valor=1):
    return Group(grupo=grupo, sin_cruce=sin_cruce, cupo_disp=cupo_disp,
                 cupo_valor=cupo_valor, horario="", fecha="")


class TestFilterCandidates:
    def test_keeps_available_no_conflict(self):
        g = _group()
        assert filter_candidates([g], require_no_conflict=True) == [g]

    def test_skips_conflict(self):
        g = _group(sin_cruce=False)
        assert filter_candidates([g], require_no_conflict=True) == []

    def test_skips_full(self):
        g = _group(cupo_disp=False, cupo_valor=0)
        assert filter_candidates([g], require_no_conflict=True) == []

    def test_conflict_allowed_when_not_required(self):
        g = _group(sin_cruce=False)
        assert filter_candidates([g], require_no_conflict=False) == [g]

    def test_picks_first_available_in_order(self):
        g1 = _group(grupo="PIG01", sin_cruce=False)
        g2 = _group(grupo="PIG02")
        g3 = _group(grupo="PIG03", cupo_disp=False, cupo_valor=0)
        assert [g.grupo for g in filter_candidates([g1, g2, g3], True)] == ["PIG02"]


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------

class FakeInputPage:
    def __init__(self):
        self.calls = []

    def eval_on_selector(self, selector, script):
        self.calls.append((selector, script))


class TestSetInput:
    def test_plain_value(self):
        page = FakeInputPage()
        set_input(page, "#isc_3Z", "alice")
        assert page.calls[0][0] == "#isc_3Z"
        assert '"alice"' in page.calls[0][1]

    def test_value_with_quotes_is_escaped(self):
        page = FakeInputPage()
        set_input(page, "#isc_42", 'pa"ss\\word')
        script = page.calls[0][1]
        # The payload must be a valid JSON string literal inside the JS
        assert '"pa\\"ss\\\\word"' in script

    def test_value_with_js_breakout_is_neutralized(self):
        page = FakeInputPage()
        value = "'); alert(1); ('"
        set_input(page, "#isc_42", value)
        script = page.calls[0][1]
        # The payload must be embedded as a JSON string literal, so any quote
        # in the value is escaped and cannot terminate the JS expression early.
        assert json.dumps(value) in script
        # And it must be assigned via a double-quoted JS literal, not raw injection
        assert 'el.value="' in script


class _Mouse:
    def click(self, x, y):
        pass


class _Keyboard:
    def press(self, key):
        pass


class FakeLoginPage:
    def __init__(self, body_text):
        self._body = body_text
        self.goto_called = False
        self.input_calls = []
        self.mouse = _Mouse()
        self.keyboard = _Keyboard()

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_called = True

    def eval_on_selector(self, selector, script):
        self.input_calls.append((selector, script))

    def evaluate(self, script):
        if "innerText" in script:
            return self._body
        return None


class TestLoginVerification:
    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        # login() contains several time.sleep calls — skip them in tests
        monkeypatch.setattr("sinu_auto.login.time.sleep", lambda s: None)

    def test_login_success_with_menu_text(self):
        page = FakeLoginPage("Bienvenido Estudiante\nSalir")
        # Should not raise
        login(page, "https://example.test", "u", "p")

    def test_login_failure_without_menu_text(self):
        page = FakeLoginPage("Página de error")
        with pytest.raises(LoginError):
            login(page, "https://example.test", "u", "p")
