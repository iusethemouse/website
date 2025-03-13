from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from generators.home import generate_home
from generators.writing import generate_writing
from generators.about import generate_about  # NEW
import shutil


def main():
    base_dir = Path(__file__).parent
    output_dir = base_dir / "output"
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"

    output_dir.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(templates_dir))

    # Generate home
    generate_home(env, output_dir)
    # Generate writing
    generate_writing(env, output_dir, base_dir)
    # Generate about
    generate_about(env, output_dir)  # NEW

    # Copy over static files
    shutil.copy2(static_dir / "styles.css", output_dir / "styles.css")
    shutil.copy2(static_dir / "icon.png", output_dir / "icon.png")
    shutil.copy2(static_dir / "humanoid.png", output_dir / "humanoid.png")


if __name__ == "__main__":
    main()
