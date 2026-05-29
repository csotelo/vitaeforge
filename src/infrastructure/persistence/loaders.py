import yaml
from domain.models import CVData, Profile, ThemeConfig


def load_cv_data(file_path: str) -> CVData:
    with open(file_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return CVData(**raw)


def load_profile(file_path: str) -> Profile:
    with open(file_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Profile(**raw)


def load_theme_config(theme_name: str) -> ThemeConfig:
    path = f"themes/{theme_name}/theme.yaml"
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ThemeConfig(**raw)
