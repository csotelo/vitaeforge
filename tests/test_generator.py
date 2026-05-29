import unittest
import yaml
from unittest.mock import patch, mock_open, MagicMock
from domain.models import (
    Lang,
    LocalizedString,
    Experience,
    CVData,
    Certification,
    CertificationCategory,
    SkillTag,
    Education,
    Course,
    ThemeConfig,
    ThemeSection,
)
from infrastructure.persistence import load_cv_data
from application.cv_generator import generate_rendercv_yaml
from entrypoints.cli import main


def make_theme(sections=None):
    """Helper: build a ThemeConfig for tests."""
    if sections is None:
        sections = [
            ThemeSection(key="summary", name="summary", optional=False),
            ThemeSection(key="experience", name="experience", optional=True),
            ThemeSection(key="entrepreneurship_experience", name="entrepreneurship_experience", optional=True),
            ThemeSection(key="skills", name="skills", optional=True),
            ThemeSection(key="education", name="education", optional=True),
            ThemeSection(key="courses_and_certifications", name="courses_and_certifications", optional=True),
            ThemeSection(key="certifications", name="certifications", optional=True),
            ThemeSection(key="other_achievements", name="other_achievements", optional=True),
            ThemeSection(key="languages", name="languages", optional=True),
        ]
    return ThemeConfig(theme_name="test", sections=sections, design={"theme": "test"})


class TestModels(unittest.TestCase):
    """Tests the Domain Entities (Clean Architecture Layer 1)"""

    def test_localized_string_behavior(self):
        loc_str = LocalizedString(es="Hola", en="Hello")
        self.assertEqual(loc_str.get(Lang.ES), "Hola")
        self.assertEqual(loc_str.get(Lang.EN), "Hello")

    def test_experience_model_defaults(self):
        exp = Experience(
            company="Test Corp",
            location=LocalizedString(es="Lima", en="Lima"),
            role=LocalizedString(es="Dev", en="Dev"),
            start_date="2020",
            end_date="2021",
            bullets=[LocalizedString(es="X", en="X")]
        )
        self.assertFalse(exp.is_entrepreneurship)
        self.assertEqual(exp.aptitudes, [])
        self.assertIsNone(exp.description)


class TestLoader(unittest.TestCase):
    """Tests the Data Access Layer (Clean Architecture Layer 2)"""

    def test_load_cv_data_parsing(self):
        sample_yaml = """
        name: Test
        lastname: User
        email: test@test.com
        phone: '123'
        website: site.com
        linkedin: in
        github: git
        location: {es: Loc, en: Loc}
        experience:
          - company: MockComp
            location: {es: L, en: L}
            role: {es: R, en: R}
            start_date: "2020"
            end_date: "2021"
            bullets: []
        skills: []
        certifications: []
        education: []
        courses: []
        """
        with patch("builtins.open", mock_open(read_data=sample_yaml)):
            result = load_cv_data("dummy_path.yaml")

        self.assertIsInstance(result, CVData)
        self.assertEqual(result.name, "Test")
        self.assertEqual(result.experience[0].company, "MockComp")


class TestGenerator(unittest.TestCase):
    """Tests the Use Cases / Logic Layer (Clean Architecture Layer 3)"""

    def setUp(self):
        self.mock_data = CVData(
            name="Juan", lastname="Perez",
            email="mail", phone="1", website="web", linkedin="in", github="git",
            location=LocalizedString(es="Loc", en="Loc"),
            experience=[
                Experience(
                    company="Corp Job", location=LocalizedString(es="L", en="L"),
                    role=LocalizedString(es="R", en="R"), start_date="2020", end_date="2021",
                    bullets=[LocalizedString(es="H1", en="H1")], is_entrepreneurship=False
                ),
                Experience(
                    company="My Startup", location=LocalizedString(es="L", en="L"),
                    role=LocalizedString(es="F", en="F"), start_date="2018", end_date="2020",
                    bullets=[], is_entrepreneurship=True,
                    description=LocalizedString(es="Desc", en="Desc"),
                    aptitudes=["Python", "AI"]
                )
            ],
            skills=[SkillTag(skill="Python", tags=["software_engineering"])],
            education=[
                Education(
                    institution="Uni A",
                    location=LocalizedString(es="L", en="L"),
                    degree=LocalizedString(es="Truncado", en="Incomplete"),
                    start_date="1997",
                    end_date="2003"
                )
            ],
            courses=[
                Course(
                    name=LocalizedString(es="Scrum", en="Scrum"),
                    issuer="3dev",
                    date="2024"
                )
            ],
            certifications=[
                Certification(name=LocalizedString(es="Pro", en="Pro"), issuer="Issuer", date="2023-01", credential_id="ID123", category=CertificationCategory.PROFESSIONAL),
            ],
        )
        self.theme = make_theme()

    def test_section_splitting_logic(self):
        yaml_output = generate_rendercv_yaml(self.mock_data, Lang.EN, self.theme)
        parsed = yaml.safe_load(yaml_output)
        sections = parsed["cv"]["sections"]

        self.assertEqual(len(sections["experience"]), 1)
        self.assertEqual(sections["experience"][0]["company"], "Corp Job")

        self.assertEqual(len(sections["entrepreneurship_experience"]), 1)
        self.assertEqual(sections["entrepreneurship_experience"][0]["company"], "My Startup")

        startup_entry = sections["entrepreneurship_experience"][0]
        self.assertIn("_Desc_", startup_entry["highlights"][0])
        self.assertTrue(any("Python, AI" in h for h in startup_entry["highlights"]))

        self.assertEqual(len(sections["certifications"]), 1)
        self.assertIn("Pro", sections["certifications"][0])

    def test_theme_section_whitelist(self):
        """Only sections declared in theme config appear in output."""
        minimal_theme = make_theme(sections=[
            ThemeSection(key="experience", name="career_history", optional=False),
        ])
        yaml_output = generate_rendercv_yaml(self.mock_data, Lang.EN, minimal_theme)
        parsed = yaml.safe_load(yaml_output)
        sections = parsed["cv"]["sections"]

        self.assertIn("career_history", sections)
        self.assertNotIn("education", sections)
        self.assertNotIn("certifications", sections)

    def test_requires_profile_section_excluded_without_profile(self):
        """Sections with requires_profile=True are skipped when no profile given."""
        theme = make_theme(sections=[
            ThemeSection(key="ats_keywords", name="summary_of_qualifications", requires_profile=True),
            ThemeSection(key="experience", name="experience", optional=True),
        ])
        yaml_output = generate_rendercv_yaml(self.mock_data, Lang.EN, theme)
        parsed = yaml.safe_load(yaml_output)
        sections = parsed["cv"]["sections"]

        self.assertNotIn("summary_of_qualifications", sections)
        self.assertIn("experience", sections)


class TestExecution(unittest.TestCase):
    """Tests the CLI entry point — role mode and jd mode."""

    @patch("sys.argv", ["vitaeforge", "--role", "data_engineer", "--lang", "en", "--auto"])
    @patch("entrypoints.cli.load_cv_data")
    @patch("entrypoints.cli.load_theme_config")
    @patch("entrypoints.cli.build_ai_adapter")
    @patch("entrypoints.cli.ProfileGenerator")
    @patch("entrypoints.cli._cv_hash", return_value="testhash")
    @patch("entrypoints.cli._find_cv_path", return_value="people/test/cv.yaml")
    @patch("entrypoints.cli.RendercvRunner")
    @patch("os.makedirs")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open,
           read_data="name: data_engineer\ntitle:\n  en: DE\n  es: DE\nsummary:\n  en: S\n  es: S\nats_keywords: []\ntheme: harmony\n_meta:\n  cv_hash: testhash\n")
    def test_role_mode_no_refresh(self, mock_file, mock_isfile, mock_makedirs,
                                   mock_runner, mock_find_cv, mock_hash, mock_pg, mock_ai, mock_theme, mock_cv):
        mock_cv.return_value = CVData(
            name="N", lastname="L",
            email="e@e.com", phone="1", location=LocalizedString(es="L", en="L"),
            experience=[], skills=[], certifications=[], education=[], courses=[],
        )
        mock_theme.return_value = make_theme()
        mock_pg.return_value.generate_profile_summaries.return_value = []
        mock_runner.return_value.render = MagicMock()

        main()

        mock_runner.return_value.render.assert_called_once()

    @patch("sys.argv", ["vitaeforge", "--jd", "jobs/test.txt", "--lang", "en", "--auto", "--theme", "harmony"])
    @patch("entrypoints.cli.load_cv_data")
    @patch("entrypoints.cli.load_theme_config")
    @patch("entrypoints.cli.build_ai_adapter")
    @patch("entrypoints.cli.JDAnalyzer")
    @patch("entrypoints.cli.ATSScorer")
    @patch("entrypoints.cli.ExperienceEnricher")
    @patch("entrypoints.cli._find_cv_path", return_value="people/test/cv.yaml")
    @patch("entrypoints.cli.RendercvRunner")
    @patch("os.makedirs")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="Senior Python Developer at Acme Corp")
    def test_jd_mode(self, mock_file, mock_isfile, mock_makedirs, mock_runner, mock_find_cv,
                     mock_enricher, mock_scorer, mock_analyzer, mock_ai, mock_theme, mock_cv):
        mock_cv.return_value = CVData(
            name="N", lastname="L",
            email="e@e.com", phone="1", location=LocalizedString(es="L", en="L"),
            experience=[], skills=[], certifications=[], education=[], courses=[],
        )
        mock_theme.return_value = make_theme()
        mock_analyzer.return_value.analyze.return_value = MagicMock(
            role_title="Python Developer", seniority="senior",
            required_keywords=["Python"], responsibilities=[], nice_to_have=[],
        )
        mock_scorer.return_value.score.return_value = MagicMock(
            score=80, headline="Dev", summary="Summary",
            missing_keywords=[], ats_keywords=["Python"],
        )
        mock_enricher.return_value.enrich.return_value = {}
        mock_runner.return_value.render = MagicMock()

        main()

        mock_runner.return_value.render.assert_called_once()
