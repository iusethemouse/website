#!/usr/bin/env python3
"""
Build script for humanoid-factoid.com
Converts Markdown content into a fully static website.
Single dependency: `markdown` (pip install markdown)
"""

import re
import shutil
from html import escape
import markdown
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"

# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


def parse_frontmatter(text):
    """Parse a --- delimited key: value block at the top of a markdown file."""
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[2]
    return meta, body


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

md = markdown.Markdown(extensions=["extra", "smarty"])


def render_md(text):
    md.reset()
    return md.convert(text)


CALLOUT_RE = re.compile(r"\[!(NOTE|WARNING|TIP)\]\n?", re.IGNORECASE)


def process_callouts(html):
    """Convert GitHub-style > [!NOTE] blockquotes into styled callouts."""
    def replace_callout(match):
        kind = match.group(1).lower()
        return f'</p></blockquote><blockquote class="callout callout-{kind}"><p><strong>{kind}</strong><br>'
    html = CALLOUT_RE.sub(replace_callout, html)
    # Clean up empty <p></p> and <blockquote></blockquote> left behind
    html = html.replace("<p></p>", "")
    html = html.replace("<blockquote>\n</blockquote>", "")
    html = html.replace("<blockquote></blockquote>", "")
    return html


def process_images(html, depth):
    """Rewrite /images/ paths to relative and wrap <img> in <figure>."""
    prefix = "../" * depth if depth else "./"
    html = html.replace('src="/images/', f'src="{prefix}images/')

    def wrap_img(match):
        tag = match.group(0)
        alt = match.group(1)
        if alt:
            return f"<figure>{tag}<figcaption>{alt}</figcaption></figure>"
        return tag

    html = re.sub(r'<img\s[^>]*?alt="([^"]*)"[^>]*/?\s*>', wrap_img, html)
    return html


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------


def base_page(title, body_html, active="", depth=0, description=""):
    prefix = "../" * depth if depth else "./"
    nav_items = [
        ("home", f"{prefix}index.html"),
        ("writing", f"{prefix}writing/index.html"),
        ("collections", f"{prefix}collections/index.html"),
        ("about", f"{prefix}about/index.html"),
    ]
    nav_links = []
    for label, href in nav_items:
        cls = ' class="active"' if label == active else ""
        nav_links.append(f'<a href="{href}"{cls}>{label}</a>')
    nav_html = " / ".join(nav_links)
    desc_tag = (
        f'\n<meta name="description" content="{escape(description, quote=True)}">'
        if description
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — humanoid's internet page</title>{desc_tag}
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
<header>
<h1>humanoid's internet page</h1>
<nav>{nav_html}</nav>
</header>
<main>
{body_html}
</main>
<footer>
<span>2026 &copy; Ivan Prigarin</span>
<span class="theme-switcher">
<button class="theme-btn" data-theme="" title="white"></button>
<button class="theme-btn" data-theme="theme-beige" title="beige"></button>
<button class="theme-btn" data-theme="theme-dark" title="dark"></button>
</span>
</footer>
<script>
(function(){{
var t=localStorage.getItem("theme");
if(t)document.body.classList.add(t);
document.querySelectorAll(".theme-btn").forEach(function(b){{
b.addEventListener("click",function(){{
document.body.classList.remove("theme-beige","theme-dark");
var th=b.dataset.theme;
if(th){{document.body.classList.add(th);localStorage.setItem("theme",th)}}
else{{localStorage.removeItem("theme")}}
}})
}})
}})()
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def build_home():
    # depth=0: output/index.html
    body = (
        '<div class="hero-drawing">'
        '<img class="hero-day" src="./images/home-day.png" alt="">'
        '<img class="hero-night" src="./images/home-night.png" alt="">'
        "</div>"
    )
    write_page(OUTPUT / "index.html", base_page("home", body, active="home", depth=0))


def build_about():
    about_file = CONTENT / "about.md"
    body = ""
    if about_file.exists():
        _, md_body = parse_frontmatter(about_file.read_text())
        body = render_md(md_body)
    body += (
        '<div class="hero-drawing">'
        '<img class="hero-day" src="../images/humanoid-day.png" alt="">'
        '<img class="hero-night" src="../images/humanoid-night.png" alt="">'
        "</div>"
    )
    dest = OUTPUT / "about"
    dest.mkdir(parents=True, exist_ok=True)
    # depth=1: output/about/index.html
    write_page(dest / "index.html", base_page("about", body, active="about", depth=1))


def build_writing():
    categories = ["technical", "non-fiction", "fiction"]

    # Index page listing all three categories
    links = []
    for cat in categories:
        cat_dir = CONTENT / "writing" / cat
        count = len(list(cat_dir.glob("*.md"))) if cat_dir.exists() else 0
        links.append(f'<li><a href="{cat}/index.html">{cat}</a> ({count})</li>')
    links_html = "".join(links)
    body = f'<ul class="category-list">{links_html}</ul>'
    dest = OUTPUT / "writing"
    dest.mkdir(parents=True, exist_ok=True)
    # depth=1: output/writing/index.html
    write_page(
        dest / "index.html", base_page("writing", body, active="writing", depth=1)
    )

    # Individual category pages
    for cat in categories:
        build_writing_category(cat)


def build_writing_category(category):
    cat_dir = CONTENT / "writing" / category
    posts = []
    if cat_dir.exists():
        for f in cat_dir.glob("*.md"):
            meta, body = parse_frontmatter(f.read_text())
            posts.append((meta, body, f.stem))
    posts.sort(key=lambda p: p[0].get("date", ""), reverse=True)

    items = []
    for meta, body, slug in posts:
        title = meta.get("title", slug)
        date = meta.get("date", "")
        date_span = f"<span>{date}</span>" if date else ""
        items.append(f'<li><a href="{slug}/index.html">{title}</a>{date_span}</li>')
    body_html = f"<h2>{category}</h2>"
    if items:
        items_html = "".join(items)
        body_html += f'<ul class="post-list">{items_html}</ul>'
    else:
        body_html += "<p>Nothing here yet.</p>"

    dest = OUTPUT / "writing" / category
    dest.mkdir(parents=True, exist_ok=True)
    # depth=2: output/writing/{category}/index.html
    write_page(
        dest / "index.html", base_page(category, body_html, active="writing", depth=2)
    )

    # Individual posts
    for meta, md_body, slug in posts:
        title = meta.get("title", slug)
        date = meta.get("date", "")
        desc = meta.get("description", "")
        content = process_callouts(process_images(render_md(md_body), depth=3))
        post_html = f"<article><h2>{title}</h2>"
        if date:
            post_html += f'<p class="post-date">{date}</p>'
        post_html += f"{content}</article>"
        post_dest = dest / slug
        post_dest.mkdir(parents=True, exist_ok=True)
        # depth=3: output/writing/{category}/{slug}/index.html
        write_page(
            post_dest / "index.html",
            base_page(title, post_html, active="writing", depth=3, description=desc),
        )


def build_collections():
    categories = ["books", "films", "tv", "games"]

    # Index page
    links = []
    for cat in categories:
        cat_dir = CONTENT / "collections" / cat
        count = len(list(cat_dir.glob("*.md"))) if cat_dir.exists() else 0
        links.append(f'<li><a href="{cat}/index.html">{cat}</a> ({count})</li>')
    links_html = "".join(links)
    body = f'<ul class="category-list">{links_html}</ul>'
    dest = OUTPUT / "collections"
    dest.mkdir(parents=True, exist_ok=True)
    # depth=1: output/collections/index.html
    write_page(
        dest / "index.html",
        base_page("collections", body, active="collections", depth=1),
    )

    # Individual category pages
    for cat in categories:
        build_collection_category(cat)


def build_subtitle(category, meta):
    """Build a category-specific subtitle from frontmatter metadata."""
    sep = " &middot; "
    parts = []

    if category == "books":
        if meta.get("author"):
            parts.append(meta["author"])
        if meta.get("series"):
            parts.append(meta["series"])
        if meta.get("year"):
            parts.append(meta["year"])

    elif category == "films":
        if meta.get("director"):
            parts.append(meta["director"])
        if meta.get("country"):
            parts.append(meta["country"])
        if meta.get("year"):
            parts.append(meta["year"])

    elif category == "tv":
        if meta.get("creator"):
            parts.append(meta["creator"])
        year_start = meta.get("year_start", "")
        year_end = meta.get("year_end", "&mdash;")
        if year_start:
            parts.append(f"{year_start}&ndash;{year_end}")
        if meta.get("seasons"):
            n = meta["seasons"]
            parts.append(f"{n} season{'s' if n != '1' else ''}")

    elif category == "games":
        if meta.get("studio"):
            parts.append(meta["studio"])
        if meta.get("year"):
            parts.append(meta["year"])
        if meta.get("genre"):
            parts.append(meta["genre"])

    return sep.join(parts)


def build_collection_category(category):
    cat_dir = CONTENT / "collections" / category
    items = []
    if cat_dir.exists():
        for f in cat_dir.glob("*.md"):
            meta, body = parse_frontmatter(f.read_text())
            items.append((meta, body, f.stem))
    items.sort(key=lambda p: p[0].get("date", ""), reverse=True)

    entries = []
    for meta, md_body, slug in items:
        title = meta.get("title", slug)
        author = meta.get("author", "")
        year = meta.get("year", "")
        cover = meta.get("cover", "")
        blurb = render_md(md_body)

        cover_html = ""
        if cover:
            cover_html = (
                f'<div class="item-cover">'
                f'<img src="../../covers/{category}/{cover}" alt="{title}">'
                f"</div>"
            )

        subtitle = build_subtitle(category, meta)

        subtitle_html = f'<p class="item-subtitle">{subtitle}</p>' if subtitle else ""
        entries.append(
            f'<div class="collection-item">'
            f"{cover_html}"
            f'<div class="item-text">'
            f"<h3>{title}</h3>"
            f"{subtitle_html}"
            f'<div class="item-blurb">{blurb}</div>'
            f"</div>"
            f"</div>"
        )

    body_html = f"<h2>{category}</h2>"
    if entries:
        body_html += "".join(entries)
    else:
        body_html += "<p>Nothing here yet.</p>"

    dest = OUTPUT / "collections" / category
    dest.mkdir(parents=True, exist_ok=True)
    # depth=2: output/collections/{category}/index.html
    write_page(
        dest / "index.html",
        base_page(category, body_html, active="collections", depth=2),
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def write_page(path, html):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)


SITE_URL = "https://humanoid-factoid.com"


def build_sitemap():
    urls = []
    for html_file in sorted(OUTPUT.rglob("*.html")):
        rel = html_file.relative_to(OUTPUT)
        # Convert path to URL: about/index.html -> /about/
        path = str(rel.parent)
        if rel.name == "index.html" and path == ".":
            urls.append("/")
        elif rel.name == "index.html":
            urls.append(f"/{path}/")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        lines.append(f"<url><loc>{SITE_URL}{url}</loc></url>")
    lines.append("</urlset>")
    (OUTPUT / "sitemap.xml").write_text("\n".join(lines))


def build_robots():
    text = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    (OUTPUT / "robots.txt").write_text(text)


def copy_static():
    """Copy static assets (CSS, cover images) into output."""
    # CSS
    css_src = STATIC / "style.css"
    if css_src.exists():
        shutil.copy2(css_src, OUTPUT / "style.css")
    # Cover images
    covers_src = STATIC / "covers"
    if covers_src.exists():
        shutil.copytree(covers_src, OUTPUT / "covers")
    # Content images
    images_src = STATIC / "images"
    if images_src.exists():
        shutil.copytree(images_src, OUTPUT / "images")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build():
    # Clean output
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()

    copy_static()
    build_home()
    build_about()
    build_writing()
    build_collections()

    build_sitemap()
    build_robots()

    page_count = len(list(OUTPUT.rglob("*.html")))
    print(f"Built {page_count} pages → {OUTPUT}/")


if __name__ == "__main__":
    build()
