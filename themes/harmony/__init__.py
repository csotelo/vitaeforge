from typing import Literal

from rendercv.schema.models.design.classic_theme import ClassicTheme


class HarmonyTheme(ClassicTheme):
    theme: Literal["harmony"] = "harmony"
