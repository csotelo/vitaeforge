import json
import unittest
from unittest.mock import MagicMock

from domain.ports import AIPort
from domain.models import CVData, Lang, LocalizedString, Experience, SkillTag, Education, Language
from domain.value_objects import JDAnalysis, ATSResult
from domain.use_cases import JDAnalyzer, ATSScorer, ExperienceEnricher


def make_ai(response: dict) -> AIPort:
    """Build a mock AIPort that returns the given dict as JSON."""
    mock = MagicMock(spec=AIPort)
    mock.complete.return_value = json.dumps(response)
    return mock


def make_cv() -> CVData:
    return CVData(
        name="Carlos", lastname="Sotelo",
        email="c@c.com", phone="1", website="w", linkedin="in", github="git",
        location=LocalizedString(es="Lima", en="Lima"),
        experience=[
            Experience(
                company="Globant",
                location=LocalizedString(es="Lima", en="Lima"),
                role=LocalizedString(es="Python Dev", en="Python Developer"),
                start_date="2021-07", end_date="2023-10",
                bullets=[],
                aptitudes=["Python", "AWS", "Scrum"],
            )
        ],
        skills=[
            SkillTag(skill="Python", tags=["software_engineering"]),
            SkillTag(skill="AWS", tags=["cloud"]),
        ],
        education=[
            Education(
                institution="UCSM",
                location=LocalizedString(es="Arequipa", en="Arequipa"),
                degree=LocalizedString(es="Ingeniería de Sistemas", en="Systems Engineering"),
                start_date="1997", end_date="2003",
            )
        ],
        certifications=[], courses=[],
        languages=[
            Language(
                name=LocalizedString(es="Inglés", en="English"),
                level=LocalizedString(es="Avanzado", en="Advanced"),
            )
        ],
    )


class TestJDAnalyzer(unittest.TestCase):

    def _valid_response(self):
        return {
            "role_title": "Senior Product Manager",
            "seniority": "senior",
            "required_keywords": ["Product Roadmap", "Agile", "OKRs", "Stakeholders"],
            "preferred_keywords": ["Jira", "SQL"],
            "responsibilities": ["Define product vision", "Manage backlog"],
        }

    def test_returns_jd_analysis(self):
        ai = make_ai(self._valid_response())
        result = JDAnalyzer(ai).analyze("some jd text")
        self.assertIsInstance(result, JDAnalysis)

    def test_role_title_extracted(self):
        ai = make_ai(self._valid_response())
        result = JDAnalyzer(ai).analyze("jd")
        self.assertEqual(result.role_title, "Senior Product Manager")

    def test_seniority_extracted(self):
        ai = make_ai(self._valid_response())
        result = JDAnalyzer(ai).analyze("jd")
        self.assertEqual(result.seniority, "senior")

    def test_keywords_are_tuples(self):
        ai = make_ai(self._valid_response())
        result = JDAnalyzer(ai).analyze("jd")
        self.assertIsInstance(result.required_keywords, tuple)
        self.assertIsInstance(result.preferred_keywords, tuple)

    def test_raw_jd_preserved(self):
        ai = make_ai(self._valid_response())
        jd_text = "We need a senior PM with OKR experience"
        result = JDAnalyzer(ai).analyze(jd_text)
        self.assertEqual(result.raw_jd, jd_text)

    def test_ai_called_once(self):
        ai = make_ai(self._valid_response())
        JDAnalyzer(ai).analyze("jd")
        ai.complete.assert_called_once()

    def test_invalid_json_raises(self):
        mock = MagicMock(spec=AIPort)
        mock.complete.return_value = "not json at all"
        with self.assertRaises(ValueError):
            JDAnalyzer(mock).analyze("jd")

    def test_tolerates_markdown_fences(self):
        mock = MagicMock(spec=AIPort)
        mock.complete.return_value = "```json\n" + json.dumps(self._valid_response()) + "\n```"
        result = JDAnalyzer(mock).analyze("jd")
        self.assertEqual(result.role_title, "Senior Product Manager")


class TestATSScorer(unittest.TestCase):

    def _jd(self):
        return JDAnalysis(
            role_title="Product Manager",
            seniority="senior",
            required_keywords=("Agile", "OKRs", "Roadmap"),
            preferred_keywords=("SQL", "Jira"),
            responsibilities=("Define vision", "Manage stakeholders"),
            raw_jd="original jd",
        )

    def _valid_response(self):
        return {
            "headline": "Senior Product Manager | Agile | OKRs",
            "summary": "Experienced PM with 20+ years...",
            "ats_keywords": ["Agile", "OKRs", "Product Roadmap"],
            "score": 72,
            "matched_keywords": ["Agile", "Python"],
            "missing_keywords": ["SQL"],
        }

    def test_returns_ats_result(self):
        ai = make_ai(self._valid_response())
        result = ATSScorer(ai).score(make_cv(), self._jd(), Lang.EN)
        self.assertIsInstance(result, ATSResult)

    def test_headline_and_summary_populated(self):
        ai = make_ai(self._valid_response())
        result = ATSScorer(ai).score(make_cv(), self._jd(), Lang.EN)
        self.assertEqual(result.headline, "Senior Product Manager | Agile | OKRs")
        self.assertIn("20+", result.summary)

    def test_score_is_int(self):
        ai = make_ai(self._valid_response())
        result = ATSScorer(ai).score(make_cv(), self._jd(), Lang.EN)
        self.assertIsInstance(result.score, int)
        self.assertEqual(result.score, 72)

    def test_keywords_are_tuples(self):
        ai = make_ai(self._valid_response())
        result = ATSScorer(ai).score(make_cv(), self._jd(), Lang.EN)
        self.assertIsInstance(result.ats_keywords, tuple)
        self.assertIsInstance(result.matched_keywords, tuple)
        self.assertIsInstance(result.missing_keywords, tuple)

    def test_ai_called_once(self):
        ai = make_ai(self._valid_response())
        ATSScorer(ai).score(make_cv(), self._jd(), Lang.EN)
        ai.complete.assert_called_once()

    def test_lang_passed_in_prompt(self):
        ai = make_ai(self._valid_response())
        ATSScorer(ai).score(make_cv(), self._jd(), Lang.ES)
        prompt_used = ai.complete.call_args[0][0]
        self.assertIn("es", prompt_used)

    def test_invalid_json_raises(self):
        mock = MagicMock(spec=AIPort)
        mock.complete.return_value = "not valid json"
        with self.assertRaises(ValueError):
            ATSScorer(mock).score(make_cv(), self._jd(), Lang.EN)


class TestExperienceEnricher(unittest.TestCase):

    def _jd(self):
        return JDAnalysis(
            role_title="Product Manager",
            seniority="mid",
            required_keywords=("Agile", "Roadmap", "Stakeholders"),
            preferred_keywords=("Jira", "OKRs"),
            responsibilities=("Define product vision", "Manage backlog"),
            raw_jd="jd text",
        )

    def _valid_response(self):
        return {
            "enrichments": [
                {"company": "Globant", "start_date": "2021-07", "bridge_bullet": "Led product discovery with 5 stakeholders to define roadmap for data platform"},
            ]
        }

    def test_returns_dict(self):
        ai = make_ai(self._valid_response())
        result = ExperienceEnricher(ai).enrich(make_cv(), self._jd(), Lang.EN)
        self.assertIsInstance(result, dict)

    def test_company_key_matches(self):
        ai = make_ai(self._valid_response())
        result = ExperienceEnricher(ai).enrich(make_cv(), self._jd(), Lang.EN)
        self.assertIn(("Globant", "2021-07"), result)

    def test_bridge_bullet_is_string(self):
        ai = make_ai(self._valid_response())
        result = ExperienceEnricher(ai).enrich(make_cv(), self._jd(), Lang.EN)
        self.assertIsInstance(result[("Globant", "2021-07")], str)
        self.assertIn("roadmap", result[("Globant", "2021-07")].lower())

    def test_empty_enrichments_returns_empty_dict(self):
        ai = make_ai({"enrichments": []})
        result = ExperienceEnricher(ai).enrich(make_cv(), self._jd(), Lang.EN)
        self.assertEqual(result, {})

    def test_ai_called_once(self):
        ai = make_ai(self._valid_response())
        ExperienceEnricher(ai).enrich(make_cv(), self._jd(), Lang.EN)
        ai.complete.assert_called_once()

    def test_invalid_json_raises(self):
        mock = MagicMock(spec=AIPort)
        mock.complete.return_value = "not valid json"
        with self.assertRaises(ValueError):
            ExperienceEnricher(mock).enrich(make_cv(), self._jd(), Lang.EN)

    def test_bridge_bullet_inserted_in_generator(self):
        import yaml
        from application.cv_generator import generate_rendercv_yaml
        from domain.models import ThemeConfig, ThemeSection
        theme = ThemeConfig(
            theme_name="t",
            sections=[ThemeSection(key="experience", name="experience", optional=False)],
            design={"theme": "t"},
        )
        summaries = {("Globant", "2021-07"): "Defined product roadmap for 3 enterprise clients"}
        output = generate_rendercv_yaml(make_cv(), Lang.EN, theme, summaries=summaries)
        parsed = yaml.safe_load(output)
        entry = parsed["cv"]["sections"]["experience"][0]
        # multi-page themes: AI text goes in summary (plain text, no bullet)
        self.assertIn("Defined product roadmap", entry["summary"])
