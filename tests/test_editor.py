import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

import yaml

from domain.ports import AIPort
from domain.use_cases import CVEditor
from infrastructure.persistence.cv_writer import (
    upsert_experience,
    upsert_project,
    upsert_education,
    upsert_skills,
    upsert_language,
    upsert_certification,
    append_course,
    append_achievement,
)


def make_ai(response: dict) -> AIPort:
    mock = MagicMock(spec=AIPort)
    mock.complete.return_value = json.dumps(response)
    return mock


def _write_cv(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def _read_cv(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class TestCVEditor(unittest.TestCase):
    """Tests the CVEditor domain use case (Clean Architecture Layer 3)."""

    _EXPERIENCE_RESPONSE = {
        "company": "Acme Corp",
        "location": {"es": "Lima, Perú", "en": "Lima, Peru"},
        "role": {"es": "Ingeniero de Datos", "en": "Data Engineer"},
        "start_date": "2022-01",
        "end_date": "2024-06",
        "is_entrepreneurship": False,
        "description": {"es": "Empresa de retail", "en": "Retail company"},
        "aptitudes": ["Python", "Spark"],
        "bullets": [
            {"es": "Logré X con Y resultado.", "en": "Achieved X with Y result."}
        ],
    }

    _PROJECT_RESPONSE = {
        "name": {"es": "Mi Proyecto", "en": "My Project"},
        "url": "https://github.com/user/proj",
        "category": "open_source",
        "start_date": "2023-03",
        "end_date": "Present",
        "bullets": [{"es": "Contribuí X.", "en": "Contributed X."}],
    }

    _SKILLS_RESPONSE = {
        "skills": [
            {"skill": "Python", "tags": ["data_engineer", "software_engineer"]},
            {"skill": "Agile", "tags": ["all"]},
        ]
    }

    _REVIEW_RESPONSE = {
        "reviewed": [
            {
                "original_en": "Did stuff.",
                "improved_en": "Automated pipeline, reducing latency by 40%.",
                "original_es": "Hice cosas.",
                "improved_es": "Automaticé pipeline, reduciendo latencia un 40%.",
            }
        ]
    }

    def test_extract_experience_returns_dict(self):
        editor = CVEditor(make_ai(self._EXPERIENCE_RESPONSE))
        result = editor.extract_experience("I worked at Acme Corp...")
        self.assertEqual(result["company"], "Acme Corp")
        self.assertEqual(result["role"]["en"], "Data Engineer")
        self.assertIsInstance(result["bullets"], list)

    def test_extract_project_returns_dict(self):
        editor = CVEditor(make_ai(self._PROJECT_RESPONSE))
        result = editor.extract_project("I built My Project...")
        self.assertEqual(result["category"], "open_source")
        self.assertEqual(result["name"]["en"], "My Project")

    def test_classify_skills_returns_list(self):
        editor = CVEditor(make_ai(self._SKILLS_RESPONSE))
        result = editor.classify_skills("Python, Agile")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["skill"], "Python")
        self.assertIn("data_engineer", result[0]["tags"])

    def test_review_bullets_returns_list(self):
        editor = CVEditor(make_ai(self._REVIEW_RESPONSE))
        result = editor.review_bullets(
            company="Acme", role="Dev", start_date="2020", end_date="2022",
            bullets=[{"en": "Did stuff.", "es": "Hice cosas."}],
        )
        self.assertEqual(len(result), 1)
        self.assertIn("latency", result[0]["improved_en"])

    def test_invalid_json_raises_value_error(self):
        mock = MagicMock(spec=AIPort)
        mock.complete.return_value = "not json at all"
        editor = CVEditor(mock)
        with self.assertRaises(ValueError):
            editor.extract_experience("any text")


class TestCVWriter(unittest.TestCase):
    """Tests the cv_writer persistence layer (Clean Architecture Layer 2)."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        self.tmp.close()
        _write_cv(self.tmp.name, {
            "experience": [
                {
                    "company": "Existing Corp",
                    "start_date": "2020-01",
                    "end_date": "2022-12",
                    "bullets": [],
                }
            ],
            "projects": [],
            "skills": [{"skill": "Python", "tags": ["software_engineer"]}],
        })

    def tearDown(self):
        os.unlink(self.tmp.name)

    # Experience

    def test_upsert_experience_appends_new(self):
        entry = {"company": "New Corp", "start_date": "2023-01", "end_date": "Present", "bullets": []}
        replaced = upsert_experience(self.tmp.name, entry)
        data = _read_cv(self.tmp.name)
        self.assertFalse(replaced)
        self.assertEqual(len(data["experience"]), 2)
        self.assertEqual(data["experience"][-1]["company"], "New Corp")

    def test_upsert_experience_replaces_existing(self):
        entry = {"company": "Existing Corp", "start_date": "2020-01", "end_date": "2022-12", "bullets": ["updated"]}
        replaced = upsert_experience(self.tmp.name, entry)
        data = _read_cv(self.tmp.name)
        self.assertTrue(replaced)
        self.assertEqual(len(data["experience"]), 1)
        self.assertEqual(data["experience"][0]["bullets"], ["updated"])

    # Project

    def test_upsert_project_appends_new(self):
        entry = {"name": {"es": "P", "en": "ProjectA"}, "category": "open_source", "start_date": "2024", "end_date": "Present", "bullets": []}
        replaced = upsert_project(self.tmp.name, entry)
        data = _read_cv(self.tmp.name)
        self.assertFalse(replaced)
        self.assertEqual(len(data["projects"]), 1)

    def test_upsert_project_replaces_existing(self):
        entry = {"name": {"es": "P", "en": "ProjectA"}, "category": "open_source", "start_date": "2024", "end_date": "Present", "bullets": []}
        upsert_project(self.tmp.name, entry)
        updated = {**entry, "start_date": "2023"}
        replaced = upsert_project(self.tmp.name, updated)
        data = _read_cv(self.tmp.name)
        self.assertTrue(replaced)
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["projects"][0]["start_date"], "2023")

    # Skills

    def test_upsert_skills_adds_new(self):
        added, updated = upsert_skills(self.tmp.name, [{"skill": "Spark", "tags": ["data_engineer"]}])
        data = _read_cv(self.tmp.name)
        self.assertEqual(added, 1)
        self.assertEqual(updated, 0)
        self.assertEqual(len(data["skills"]), 2)

    def test_upsert_skills_updates_existing(self):
        added, updated = upsert_skills(self.tmp.name, [{"skill": "Python", "tags": ["software_engineer", "data_engineer"]}])
        data = _read_cv(self.tmp.name)
        self.assertEqual(added, 0)
        self.assertEqual(updated, 1)
        self.assertIn("data_engineer", data["skills"][0]["tags"])

    # Education

    def test_upsert_education_appends(self):
        entry = {"institution": "MIT", "start_date": "2015", "end_date": "2019", "location": {"es": "L", "en": "L"}, "degree": {"es": "D", "en": "D"}}
        replaced = upsert_education(self.tmp.name, entry)
        data = _read_cv(self.tmp.name)
        self.assertFalse(replaced)
        self.assertEqual(data["education"][0]["institution"], "MIT")

    # Language

    def test_upsert_language_appends_and_replaces(self):
        entry = {"name": {"es": "Inglés", "en": "English"}, "level": {"es": "B2", "en": "B2"}}
        upsert_language(self.tmp.name, entry)
        updated = {"name": {"es": "Inglés", "en": "English"}, "level": {"es": "C1", "en": "C1"}}
        replaced = upsert_language(self.tmp.name, updated)
        data = _read_cv(self.tmp.name)
        self.assertTrue(replaced)
        self.assertEqual(len(data["languages"]), 1)
        self.assertEqual(data["languages"][0]["level"]["en"], "C1")

    # Certification

    def test_upsert_certification_appends_and_replaces(self):
        entry = {"name": {"es": "Cert", "en": "Cert"}, "issuer": "Body", "date": "2023-01", "credential_id": "ABC123", "category": "professional"}
        upsert_certification(self.tmp.name, entry)
        updated = {**entry, "date": "2024-01"}
        replaced = upsert_certification(self.tmp.name, updated)
        data = _read_cv(self.tmp.name)
        self.assertTrue(replaced)
        self.assertEqual(len(data["certifications"]), 1)
        self.assertEqual(data["certifications"][0]["date"], "2024-01")

    # Course and Achievement (append-only)

    def test_append_course(self):
        append_course(self.tmp.name, {"name": {"es": "C", "en": "C"}, "issuer": "X", "date": "2023-01"})
        append_course(self.tmp.name, {"name": {"es": "D", "en": "D"}, "issuer": "Y", "date": "2023-06"})
        data = _read_cv(self.tmp.name)
        self.assertEqual(len(data["courses"]), 2)

    def test_append_achievement(self):
        append_achievement(self.tmp.name, {"es": "Logro A", "en": "Achievement A"})
        data = _read_cv(self.tmp.name)
        self.assertEqual(len(data["achievements"]), 1)
        self.assertEqual(data["achievements"][0]["en"], "Achievement A")
