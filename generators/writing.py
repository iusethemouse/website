import os
import yaml
import markdown
from pathlib import Path


def parse_post(file_path):
    with open(file_path, "r") as f:
        content = f.read()
        _, front_matter, body = content.split("---", 2)
        metadata = yaml.safe_load(front_matter)
        html_content = markdown.markdown(body, extensions=["fenced_code"])
        url = f"{metadata['title'].replace(' ', '_').lower()}.html"
        return {**metadata, "content": html_content, "url": url}


def generate_post_page(env, output_dir, post_data):
    template = env.get_template("post.html")
    output = template.render(**post_data)

    with open(f"{output_dir}/{post_data['url']}", "w") as f:
        f.write(output)


def generate_writing(env, output_dir, content_dir):
    posts_dir = Path(content_dir) / "writing"
    posts = []

    if posts_dir.exists():
        for file in posts_dir.glob("*.md"):
            post_data = parse_post(file)
            posts.append(post_data)
            generate_post_page(env, output_dir, post_data)

    # Sort posts by date, latest first
    posts.sort(key=lambda x: x["date"], reverse=True)

    template = env.get_template("writing.html")
    output = template.render(posts=posts)

    with open(f"{output_dir}/writing.html", "w") as f:
        f.write(output)
