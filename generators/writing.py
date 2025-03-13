from pathlib import Path
from .utils import parse_md_file


def generate_post_page(env, output_dir, post_data):
    template = env.get_template("post.html")
    output = template.render(**post_data)

    with open(output_dir / post_data["url"], "w", encoding="utf-8") as f:
        f.write(output)


def generate_writing(env, output_dir, content_dir):

    def parse_directory(dir_path):
        posts = []
        if dir_path.exists():
            for md_file in dir_path.glob("*.md"):
                post_data = parse_md_file(md_file, use_fenced_code=True)

                slug = post_data["title"].replace(" ", "_").lower()
                post_data["url"] = f"{slug}.html"

                generate_post_page(env, output_dir, post_data)
                posts.append(post_data)

        # Sort posts by date descending
        posts.sort(key=lambda x: x.get("date", ""), reverse=True)
        return posts

    fiction_dir = Path(content_dir) / "writing" / "fiction"
    nonfiction_dir = Path(content_dir) / "writing" / "non-fiction"
    technical_dir = Path(content_dir) / "writing" / "technical"

    fiction_posts = parse_directory(fiction_dir)
    nonfiction_posts = parse_directory(nonfiction_dir)
    technical_posts = parse_directory(technical_dir)

    template = env.get_template("writing.html")
    output = template.render(
        fiction_posts=fiction_posts,
        nonfiction_posts=nonfiction_posts,
        technical_posts=technical_posts,
    )

    with open(output_dir / "writing.html", "w", encoding="utf-8") as f:
        f.write(output)
