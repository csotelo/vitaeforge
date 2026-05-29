import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

from domain.ports import AIPort
from domain.models import CVData, Lang, LocalizedString, ThemeConfig, ThemeSection
from domain.value_objects import JDAnalysis, ATSResult
from entrypoints.cli import _slugify, main, _find_cv_path


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_cv():
    return CVData(
        name="Carlos", lastname="Sotelo",
        email="c@c.com", phone="1", website="https://dev.to", linkedin="in", github="git",
        location=LocalizedString(es="Lima", en="Lima"),
        experience=[], skills=[], certifications=[], education=[], courses=[],
    )

def _make_theme():
    return ThemeConfig(
        theme_name="harmony",
        sections=[ThemeSection(key="summary", name="Profile", optional=True)],
        design={"theme": "harmony"},
    )

def _jd_ai_response():
    return json.dumps({
        "role_title": "Senior Product Manager",
        "seniority": "senior",
        "required_keywords": ["Agile", "OKRs", "Roadmap"],
        "preferred_keywords": ["SQL"],
        "responsibilities": ["Define vision", "Manage backlog"],
    })

def _ats_ai_response():
    return json.dumps({
        "headline": "Senior PM | Agile | OKRs",
        "summary": "Experienced PM with 20+ years driving product strategy.",
        "ats_keywords": ["Agile", "OKRs"],
        "score": 75,
        "matched_keywords": ["Agile"],
        "missing_keywords": ["SQL"],
    })

def _enricher_ai_response():
    return json.dumps({"enrichments": []})


# ── Unit tests ─────────────────────────────────────────────────────────────────

class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_slugify("Senior Product Manager"), "senior_product_manager")

    def test_special_chars(self):
        self.assertEqual(_slugify("C++ / Python Developer"), "c_python_developer")

    def test_max_length(self):
        self.assertLessEqual(len(_slugify("a" * 100)), 40)


# ── JD mode ────────────────────────────────────────────────────────────────────

class TestJDMode(unittest.TestCase):
    def _argv(self, extra=None):
        sys.argv = ["vitaeforge", "--jd", "jobs/job.txt", "--lang", "en", "--auto"] + (extra or [])

    @patch("entrypoints.cli.RendercvRunner")
    @patch("entrypoints.cli.generate_rendercv_yaml", return_value="yaml: content")
    @patch("entrypoints.cli.load_theme_config")
    @patch("entrypoints.cli.load_cv_data")
    @patch("entrypoints.cli.build_ai_adapter")
    @patch("entrypoints.cli._find_cv_path", return_value="people/test/cv.yaml")
    @patch("builtins.open", mock_open(read_data="We need a senior PM with Agile skills."))
    @patch("os.path.isfile", return_value=True)
    @patch("os.makedirs")
    def test_full_flow(self, mock_makedirs, mock_isfile, mock_find_cv, mock_ai_factory,
                       mock_load_cv, mock_load_theme, mock_generate, mock_runner):
        ai_mock = MagicMock(spec=AIPort)
        ai_mock.complete.side_effect = [_jd_ai_response(), _ats_ai_response(), _enricher_ai_response()]
        mock_ai_factory.return_value = ai_mock
        mock_load_cv.return_value = _make_cv()
        mock_load_theme.return_value = _make_theme()
        mock_runner.return_value.render = MagicMock()

        self._argv()
        main()

        self.assertEqual(ai_mock.complete.call_count, 3)
        mock_generate.assert_called_once()
        mock_runner.return_value.render.assert_called_once()

    def test_missing_cv_exits(self):
        self._argv()
        with patch("os.path.isfile", return_value=False):
            with self.assertRaises(SystemExit):
                main()

    def test_unknown_model_exits(self):
        self._argv(["--model", "nonexistent-xyz"])
        with patch("os.path.isfile", return_value=True):
            with patch("entrypoints.cli.load_cv_data", return_value=_make_cv()):
                with patch("entrypoints.cli.load_theme_config", return_value=_make_theme()):
                    with self.assertRaises(SystemExit):
                        main()


# ── Role mode ──────────────────────────────────────────────────────────────────

class TestRoleMode(unittest.TestCase):
    def _argv(self, extra=None):
        sys.argv = ["vitaeforge", "--role", "data_engineer", "--lang", "en"] + (extra or [])

    _PROFILE_YAML = (
        "name: data_engineer\n"
        "title:\n  en: Data Engineer\n  es: Data Engineer\n"
        "summary:\n  en: Summary.\n  es: Resumen.\n"
        "ats_keywords: [Python, SQL]\n"
        "theme: harmony\n"
        "_meta:\n  cv_hash: current123\n"
    )

    @patch("entrypoints.cli.RendercvRunner")
    @patch("entrypoints.cli.generate_rendercv_yaml", return_value="yaml: content")
    @patch("entrypoints.cli.load_theme_config")
    @patch("entrypoints.cli.load_cv_data")
    @patch("entrypoints.cli.build_ai_adapter")
    @patch("entrypoints.cli.ProfileGenerator")
    @patch("entrypoints.cli._cv_hash", return_value="current123")
    @patch("entrypoints.cli._find_cv_path", return_value="people/test/cv.yaml")
    @patch("os.path.isfile", return_value=True)
    @patch("os.makedirs")
    @patch("builtins.open", mock_open(read_data=_PROFILE_YAML))
    def test_role_up_to_date(self, mock_makedirs, mock_isfile, mock_find_cv,
                              mock_hash, mock_pg, mock_ai, mock_load_cv, mock_load_theme,
                              mock_generate, mock_runner):
        mock_load_cv.return_value = _make_cv()
        mock_load_theme.return_value = _make_theme()
        mock_pg.return_value.generate_profile_summaries.return_value = []
        mock_runner.return_value.render = MagicMock()

        self._argv()
        main()

        mock_generate.assert_called_once()
        mock_runner.return_value.render.assert_called_once()

    @patch("entrypoints.cli.RendercvRunner")
    @patch("entrypoints.cli.generate_rendercv_yaml", return_value="yaml: content")
    @patch("entrypoints.cli.load_theme_config")
    @patch("entrypoints.cli.load_cv_data")
    @patch("entrypoints.cli.build_ai_adapter")
    @patch("entrypoints.cli.ProfileGenerator")
    @patch("entrypoints.cli._cv_hash", return_value="newhash999")
    @patch("entrypoints.cli._find_cv_path", return_value="people/test/cv.yaml")
    @patch("os.path.isfile", return_value=True)
    @patch("os.makedirs")
    @patch("builtins.open", mock_open(read_data=_PROFILE_YAML))
    def test_role_refreshes_when_cv_changed(self, mock_makedirs, mock_isfile, mock_find_cv,
                                             mock_hash, mock_pg, mock_ai,
                                             mock_load_cv, mock_load_theme,
                                             mock_generate, mock_runner):
        mock_load_cv.return_value = _make_cv()
        mock_load_theme.return_value = _make_theme()
        mock_pg.return_value.generate.return_value = {
            "title_en": "DE", "title_es": "IE",
            "summary_en": "S", "summary_es": "R",
        }
        mock_pg.return_value.generate_profile_summaries.return_value = []
        mock_runner.return_value.render = MagicMock()

        self._argv()
        main()

        mock_pg.return_value.generate.assert_called_once()
        mock_generate.assert_called_once()
