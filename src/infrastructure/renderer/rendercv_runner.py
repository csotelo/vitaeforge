import os
import shutil
import subprocess
import sys


class RendercvRunner:
    """Infrastructure adapter: runs rendercv as a subprocess."""

    def render(self, yaml_path: str, pdf_path: str, theme_dir: str | None = None) -> str:
        """
        Render YAML to PDF.
        Both paths can be relative or absolute; returns the absolute PDF path.

        theme_dir: path to a custom theme directory (e.g. "themes/harmony").
          If provided and the theme is not yet present next to the YAML,
          it will be copied there before invoking rendercv.
        """
        yaml_abs = os.path.abspath(yaml_path)
        pdf_abs  = os.path.abspath(pdf_path)
        os.makedirs(os.path.dirname(pdf_abs), exist_ok=True)

        if theme_dir:
            theme_abs = os.path.abspath(theme_dir)
            if os.path.isdir(theme_abs):
                theme_name = os.path.basename(theme_abs)
                dst = os.path.join(os.path.dirname(yaml_abs), theme_name)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(theme_abs, dst)

        result = subprocess.run(
            [
                sys.executable, "-m", "rendercv", "render", yaml_abs,
                "--pdf-path", pdf_abs,
                "-nohtml", "-nomd", "-nopng",
            ],
            cwd=os.path.dirname(yaml_abs),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"rendercv failed:\n{result.stderr}")

        return pdf_abs
