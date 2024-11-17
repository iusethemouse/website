from pathlib import Path
from .utils import parse_md_file


def generate_reading(env, output_dir, content_dir):
    template = env.get_template("reading.html")

    current_books = []
    later_books = []
    completed_books = []

    # current books
    now_dir = Path(content_dir) / "reading" / "now"
    if now_dir.exists():
        for file in now_dir.glob("*.md"):
            current_books.append(parse_md_file(file))

    # later books
    later_dir = Path(content_dir) / "reading" / "later"
    if later_dir.exists():
        for file in later_dir.glob("*.md"):
            later_books.append(parse_md_file(file))

    # completed books
    read_dir = Path(content_dir) / "reading" / "read"
    if read_dir.exists():
        for file in read_dir.glob("*.md"):
            completed_books.append(parse_md_file(file))

    # Sort books maybe ??
    completed_books.sort(key=lambda x: x.get("date", ""), reverse=True)

    output = template.render(
        current_books=current_books,
        later_books=later_books,
        completed_books=completed_books,
    )

    with open(f"{output_dir}/reading.html", "w") as f:
        f.write(output)
