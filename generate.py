from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from generators.home import generate_home
from generators.reading import generate_reading
from generators.writing import generate_writing
from generators.watching import generate_watching
import shutil


def main():
    base_dir = Path(__file__).parent
    output_dir = base_dir / "output"
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"

    output_dir.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(templates_dir))

    generate_home(env, output_dir)
    generate_reading(env, output_dir, base_dir)
    generate_writing(env, output_dir, base_dir)
    generate_watching(env, output_dir, base_dir)

    shutil.copy2(static_dir / "styles.css", output_dir / "styles.css")


if __name__ == "__main__":
    main()
