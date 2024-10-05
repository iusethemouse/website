import os
import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

# Paths
POSTS_DIR = "posts"
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "output"

# Load templates
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
base_template = env.get_template("base.html")
post_template = env.get_template("post.html")

# Create output directory if not exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_markdown(file_path):
    """
    Parse Markdown file and return metadata and HTML content.
    """
    with open(file_path, "r") as f:
        content = f.read()
        _, front_matter, body = content.split("---", 2)
        metadata = yaml.safe_load(front_matter)
        html_content = markdown.markdown(body)
    return metadata, html_content


def generate_post(metadata, content):
    """
    Generate an HTML page for a given post.
    """
    output_path = os.path.join(
        OUTPUT_DIR, f"{metadata['title'].replace(' ', '_').lower()}.html"
    )
    rendered_post = post_template.render(
        title=metadata["title"], date=metadata["date"], content=content
    )
    with open(output_path, "w") as f:
        f.write(rendered_post)


def generate_index(posts):
    """
    Generate the index.html page with links to all posts.
    """
    rendered_index = base_template.render(posts=posts)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(rendered_index)


def main():
    posts_metadata = []

    # Process each markdown file in POSTS_DIR
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            file_path = os.path.join(POSTS_DIR, filename)
            metadata, html_content = parse_markdown(file_path)
            generate_post(metadata, html_content)
            posts_metadata.append(metadata)

    # Sort posts by date, latest first
    posts_metadata.sort(key=lambda x: x["date"], reverse=True)
    generate_index(posts_metadata)


if __name__ == "__main__":
    main()
