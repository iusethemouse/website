#!/usr/bin/env python3
"""
Build script for humanoid-factoid.com
Converts Markdown content and source images into a fully static website.
Dependencies are pinned in requirements.txt.
"""

import hashlib
import io
import json
import re
import shutil
import xml.etree.ElementTree as etree
from datetime import date
from html import escape
from pathlib import Path

import markdown
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from PIL import Image, ImageCms, ImageOps

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"

WRITING_CATEGORIES = ("technical", "non-fiction", "fiction")
COLLECTION_FIELDS = {
    "books": ("author", "series", "year"),
    "films": ("director", "country", "year"),
    "tv": ("creator", "year_start", "year_end", "seasons"),
    "games": ("studio", "year", "genre"),
}
COLLECTION_CATEGORIES = tuple(COLLECTION_FIELDS)

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
YEAR_RE = re.compile(r"\d{4}\Z")
DATE_RE = re.compile(
    r"(?:19|20)\d{2}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?\Z"
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class BuildError(Exception):
    """A content problem that should stop deployment with a useful message."""

# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


def parse_frontmatter(text, source="content"):
    """Parse a --- delimited key: value block at the top of a markdown file."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise BuildError(f"{source}: expected frontmatter to start with ---")

    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise BuildError(f"{source}: frontmatter has no closing ---") from exc

    meta = {}
    for line_number, line in enumerate(lines[1:closing], start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise BuildError(
                f"{source}:{line_number}: expected a key: value frontmatter line"
            )
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise BuildError(f"{source}:{line_number}: key and value cannot be empty")
        if key in meta:
            raise BuildError(f"{source}:{line_number}: duplicate frontmatter key {key!r}")
        meta[key] = value

    body = "\n".join(lines[closing + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return meta, body


def validate_slug(slug, source):
    if not SLUG_RE.fullmatch(slug):
        raise BuildError(
            f"{source}: filename must be a lowercase ASCII slug such as my-entry.md"
        )


def validate_date(value, source):
    if not DATE_RE.fullmatch(value):
        raise BuildError(f"{source}: date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    if len(value) == 10:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise BuildError(f"{source}: date is not a real calendar date") from exc


def validate_meta(meta, *, source, allowed, required):
    unknown = sorted(set(meta) - set(allowed))
    if unknown:
        raise BuildError(f"{source}: unknown frontmatter field(s): {', '.join(unknown)}")
    missing = sorted(set(required) - set(meta))
    if missing:
        raise BuildError(f"{source}: missing frontmatter field(s): {', '.join(missing)}")
    if "date" in meta:
        validate_date(meta["date"], source)
    for field in ("year", "year_start", "year_end"):
        if field in meta and not YEAR_RE.fullmatch(meta[field]):
            raise BuildError(f"{source}: {field} must be a four-digit year")
    if "seasons" in meta and (not meta["seasons"].isdigit() or int(meta["seasons"]) < 1):
        raise BuildError(f"{source}: seasons must be a positive number")


def read_writing_file(path):
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
    validate_slug(path.stem, path)
    validate_meta(
        meta,
        source=path,
        allowed=("title", "date", "description"),
        required=("title", "date"),
    )
    return meta, body


def read_collection_file(path, category):
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
    validate_slug(path.stem, path)
    allowed = ("title", "date", "cover", *COLLECTION_FIELDS[category])
    validate_meta(meta, source=path, allowed=allowed, required=("title", "date"))
    return meta, body


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

class CalloutProcessor(BlockProcessor):
    """Render GitHub-style > [!NOTE] blockquotes without rewriting HTML."""

    RE = re.compile(r"^>\s*\[!(NOTE|WARNING|TIP)\]\s*(?:\n|$)", re.IGNORECASE)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        match = self.RE.match(block)
        kind = match.group(1).lower()
        remainder = block[match.end() :]
        lines = [re.sub(r"^>\s?", "", line) for line in remainder.splitlines()]

        callout = etree.SubElement(
            parent, "blockquote", {"class": f"callout callout-{kind}"}
        )
        label = etree.SubElement(callout, "strong")
        label.text = kind
        content = "\n".join(lines).strip()
        if content:
            self.parser.parseBlocks(callout, [content])


class CalloutExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            CalloutProcessor(md.parser), "humanoid_callout", 21
        )


md = markdown.Markdown(extensions=["extra", "smarty", CalloutExtension()])


def render_md(text):
    md.reset()
    return md.convert(text)


def process_images(html, depth, image_manifest):
    """Rewrite /images/ paths to relative and wrap <img> in <figure>."""
    prefix = "../" * depth if depth else "./"
    for source_name, asset in image_manifest.items():
        html = html.replace(
            f'src="/images/{source_name}"',
            f'src="{prefix}images/{asset["filename"]}" '
            f'width="{asset["width"]}" height="{asset["height"]}" '
            'loading="lazy" decoding="async"',
        )
    missing = re.findall(r'src="/images/([^"]+)"', html)
    if missing:
        raise BuildError(f"missing or unsupported content image(s): {', '.join(missing)}")
    html = html.replace('src="/images/', f'src="{prefix}images/')

    def wrap_img(match):
        tag = match.group(0)
        alt = match.group(1)
        if alt:
            return f"<figure>{tag}<figcaption>{alt}</figcaption></figure>"
        return tag

    html = re.sub(r'<img\s[^>]*?alt="([^"]*)"[^>]*/?\s*>', wrap_img, html)
    return html


def _srgb_image(image):
    """Apply an embedded colour profile and return RGB pixels in sRGB."""
    rgb = image.convert("RGB")
    profile = image.info.get("icc_profile")
    if not profile:
        return rgb
    try:
        return ImageCms.profileToProfile(
            rgb,
            ImageCms.ImageCmsProfile(io.BytesIO(profile)),
            ImageCms.createProfile("sRGB"),
            outputMode="RGB",
        )
    except (OSError, ValueError):
        return rgb


def optimize_image(source, destination, *, max_edge, lossless=False):
    """Create the smallest suitable PNG/WebP/JPEG derivative for one image."""
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
    except (OSError, ValueError) as exc:
        raise BuildError(f"{source}: could not read image: {exc}") from exc

    if max(image.size) > max_edge:
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    candidates = []
    if lossless or "A" in image.getbands() or image.mode == "P":
        source_rgba = image.convert("RGBA")
        rgba = _srgb_image(source_rgba).convert("RGBA")
        rgba.putalpha(source_rgba.getchannel("A"))
        png = io.BytesIO()
        rgba.save(png, "PNG", optimize=True)
        candidates.append((".png", png.getvalue()))

        webp = io.BytesIO()
        rgba.save(webp, "WEBP", lossless=True, method=6)
        candidates.append((".webp", webp.getvalue()))
    else:
        rgb = _srgb_image(image)
        jpeg = io.BytesIO()
        rgb.save(jpeg, "JPEG", quality=85, optimize=True, progressive=True)
        candidates.append((".jpg", jpeg.getvalue()))

        webp = io.BytesIO()
        rgb.save(webp, "WEBP", quality=82, method=6)
        candidates.append((".webp", webp.getvalue()))

    suffix, data = min(candidates, key=lambda candidate: len(candidate[1]))
    digest = hashlib.sha256(data).hexdigest()[:12]
    filename = f"{source.stem}.{digest}{suffix}"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / filename).write_bytes(data)
    return {"filename": filename, "width": image.width, "height": image.height}


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------


def base_page(
    title,
    body_html,
    active="",
    depth=0,
    description="",
    robots="",
    scripts=(),
):
    prefix = "../" * depth if depth else "./"
    style_version = hashlib.sha256((STATIC / "style.css").read_bytes()).hexdigest()[:12]
    theme_version = hashlib.sha256((STATIC / "theme.js").read_bytes()).hexdigest()[:12]
    nav_items = [
        ("home", f"{prefix}index.html"),
        ("writing", f"{prefix}writing/index.html"),
        ("collections", f"{prefix}collections/index.html"),
        ("about", f"{prefix}about/index.html"),
    ]
    nav_links = []
    for label, href in nav_items:
        attrs = ' class="active" aria-current="page"' if label == active else ""
        nav_links.append(f'<a href="{href}"{attrs}>{label}</a>')
    nav_html = " / ".join(nav_links)
    desc_tag = (
        f'\n<meta name="description" content="{escape(description, quote=True)}">'
        if description
        else ""
    )
    robots_tag = (
        f'\n<meta name="robots" content="{escape(robots, quote=True)}">'
        if robots
        else ""
    )
    extra_scripts = "".join(
        f'\n<script src="{prefix}{escape(script, quote=True)}?v='
        f'{hashlib.sha256((STATIC / script).read_bytes()).hexdigest()[:12]}" defer></script>'
        for script in scripts
    )
    safe_title = escape(title)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title} — humanoid's internet page</title>{desc_tag}{robots_tag}
<link rel="stylesheet" href="{prefix}style.css?v={style_version}">
<script src="{prefix}theme.js?v={theme_version}" defer></script>{extra_scripts}
</head>
<body>
<header>
<p class="site-title">humanoid's internet page</p>
<nav>{nav_html}</nav>
</header>
<main>
{body_html}
</main>
<footer>
<span>{date.today().year} &copy; Ivan Prigarin</span>
<span class="theme-switcher">
<button class="theme-btn" type="button" data-theme="" aria-label="Use white theme"></button>
<button class="theme-btn" type="button" data-theme="theme-beige" aria-label="Use beige theme"></button>
<button class="theme-btn" type="button" data-theme="theme-dark" aria-label="Use dark theme"></button>
</span>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def build_home(image_manifest):
    # depth=0: output/index.html
    day = image_manifest["home-day.png"]
    night = image_manifest["home-night.png"]
    body = (
        '<div class="hero-drawing">'
        f'<img class="hero-day" src="./images/{day["filename"]}" alt="" '
        f'width="{day["width"]}" height="{day["height"]}">'
        f'<img class="hero-night" src="./images/{night["filename"]}" alt="" '
        f'width="{night["width"]}" height="{night["height"]}">'
        "</div>"
    )
    write_page(OUTPUT / "index.html", base_page("home", body, active="home", depth=0))


def build_about(image_manifest):
    about_file = CONTENT / "about.md"
    body = ""
    if about_file.exists():
        meta, md_body = parse_frontmatter(
            about_file.read_text(encoding="utf-8"), about_file
        )
        validate_meta(
            meta,
            source=about_file,
            allowed=("title",),
            required=("title",),
        )
        body = render_md(md_body)
    day = image_manifest["humanoid-day.png"]
    night = image_manifest["humanoid-night.png"]
    body += (
        '<div class="hero-drawing">'
        f'<img class="hero-day" src="../images/{day["filename"]}" alt="" '
        f'width="{day["width"]}" height="{day["height"]}">'
        f'<img class="hero-night" src="../images/{night["filename"]}" alt="" '
        f'width="{night["width"]}" height="{night["height"]}">'
        "</div>"
    )
    dest = OUTPUT / "about"
    dest.mkdir(parents=True, exist_ok=True)
    # depth=1: output/about/index.html
    write_page(dest / "index.html", base_page("about", body, active="about", depth=1))


def build_writing(image_manifest):
    # Index page listing all three categories
    links = []
    for cat in WRITING_CATEGORIES:
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
    for cat in WRITING_CATEGORIES:
        build_writing_category(cat, image_manifest)


def build_writing_category(category, image_manifest):
    cat_dir = CONTENT / "writing" / category
    posts = []
    if cat_dir.exists():
        for f in cat_dir.glob("*.md"):
            meta, body = read_writing_file(f)
            posts.append((meta, body, f.stem))
    posts.sort(key=lambda p: (p[0]["title"].casefold(), p[2]))
    posts.sort(key=lambda p: p[0]["date"], reverse=True)

    items = []
    for meta, body, slug in posts:
        title = escape(meta["title"])
        entry_date = escape(meta["date"])
        date_span = f'<time datetime="{entry_date}">{entry_date}</time>'
        items.append(f'<li><a href="{slug}/index.html">{title}</a>{date_span}</li>')
    body_html = f"<h1>{escape(category)}</h1>"
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
        title = meta["title"]
        entry_date = meta["date"]
        desc = meta.get("description", "")
        content = process_images(render_md(md_body), depth=3, image_manifest=image_manifest)
        post_html = f"<article><h1>{escape(title)}</h1>"
        if entry_date:
            safe_date = escape(entry_date)
            post_html += (
                f'<p class="post-date"><time datetime="{safe_date}">'
                f"{safe_date}</time></p>"
            )
        post_html += f"{content}</article>"
        post_dest = dest / slug
        post_dest.mkdir(parents=True, exist_ok=True)
        # depth=3: output/writing/{category}/{slug}/index.html
        write_page(
            post_dest / "index.html",
            base_page(title, post_html, active="writing", depth=3, description=desc),
        )


def build_collections(cover_manifest):
    # Index page
    links = []
    for cat in COLLECTION_CATEGORIES:
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
    for cat in COLLECTION_CATEGORIES:
        build_collection_category(cat, cover_manifest)


def build_subtitle(category, meta):
    """Build a category-specific subtitle from frontmatter metadata."""
    sep = " &middot; "
    parts = []

    if category == "books":
        if meta.get("author"):
            parts.append(escape(meta["author"]))
        if meta.get("series"):
            parts.append(escape(meta["series"]))
        if meta.get("year"):
            parts.append(escape(meta["year"]))

    elif category == "films":
        if meta.get("director"):
            parts.append(escape(meta["director"]))
        if meta.get("country"):
            parts.append(escape(meta["country"]))
        if meta.get("year"):
            parts.append(escape(meta["year"]))

    elif category == "tv":
        if meta.get("creator"):
            parts.append(escape(meta["creator"]))
        year_start = meta.get("year_start", "")
        year_end = meta.get("year_end", "present")
        if year_start:
            parts.append(f"{escape(year_start)}&ndash;{escape(year_end)}")
        if meta.get("seasons"):
            n = meta["seasons"]
            parts.append(f"{escape(n)} season{'s' if n != '1' else ''}")

    elif category == "games":
        if meta.get("studio"):
            parts.append(escape(meta["studio"]))
        if meta.get("year"):
            parts.append(escape(meta["year"]))
        if meta.get("genre"):
            parts.append(escape(meta["genre"]))

    return sep.join(parts)


def build_collection_category(category, cover_manifest):
    cat_dir = CONTENT / "collections" / category
    items = []
    if cat_dir.exists():
        for f in cat_dir.glob("*.md"):
            meta, body = read_collection_file(f, category)
            items.append((meta, body, f.stem))
    items.sort(key=lambda p: (p[0]["title"].casefold(), p[2]))
    items.sort(key=lambda p: p[0]["date"], reverse=True)

    entries = []
    for index, (meta, md_body, slug) in enumerate(items):
        title = meta["title"]
        cover = meta.get("cover", "")
        blurb = render_md(md_body)

        cover_html = ""
        if cover:
            key = f"{category}/{cover}"
            asset = cover_manifest.get(key)
            if not asset:
                raise BuildError(
                    f"{cat_dir / f'{slug}.md'}: cover does not exist: {cover}"
                )
            loading = "" if index == 0 else ' loading="lazy"'
            cover_html = (
                f'<div class="item-cover">'
                f'<img src="../../covers/{category}/{asset["filename"]}" '
                f'alt="{escape(title, quote=True)}" width="{asset["width"]}" '
                f'height="{asset["height"]}" decoding="async"{loading}>'
                f"</div>"
            )

        subtitle = build_subtitle(category, meta)

        subtitle_html = f'<p class="item-subtitle">{subtitle}</p>' if subtitle else ""
        entries.append(
            f'<div class="collection-item">'
            f"{cover_html}"
            f'<div class="item-text">'
            f"<h2>{escape(title)}</h2>"
            f"{subtitle_html}"
            f'<div class="item-blurb">{blurb}</div>'
            f"</div>"
            f"</div>"
        )

    body_html = f"<h1>{escape(category)}</h1>"
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
    path.write_text(html, encoding="utf-8")


SITE_URL = "https://humanoid-factoid.com"


def build_sitemap():
    urls = []
    for html_file in sorted(OUTPUT.rglob("*.html")):
        rel = html_file.relative_to(OUTPUT)
        if rel.parts[0] == "admin":
            continue
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
    (OUTPUT / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def build_robots():
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    (OUTPUT / "robots.txt").write_text(text, encoding="utf-8")


def build_admin():
    categories = "".join(
        f'<option value="{category}">{category}</option>'
        for category in COLLECTION_CATEGORIES
    )
    body = f"""
<section class="admin-panel">
<h1>add to site</h1>
<p>This creates a Markdown file and any associated assets in one Git commit.</p>
<form id="admin-form" action="./submit" method="post" enctype="multipart/form-data">
<label>entry type
<select id="entry-type" name="entry_type">
<option value="collection">collection</option>
<option value="writing">writing</option>
</select>
</label>
<label>category
<select id="category" name="category">{categories}</select>
</label>
<label>title
<input id="title" name="title" type="text" maxlength="200" required>
</label>
<div id="category-fields"></div>
<label>slug
<input id="slug" name="slug" type="text" maxlength="120" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" required>
<small>lowercase letters, numbers, and hyphens; used as the filename</small>
</label>
<label><span id="date-label">date experienced</span>
<input id="entry-date" name="date" type="text" maxlength="10" placeholder="YYYY, YYYY-MM, or YYYY-MM-DD" required>
</label>
<div id="collection-fields">
<label>cover image <span class="optional">optional</span>
<input id="cover" name="cover" type="file" accept="image/jpeg,image/png,image/webp">
<small>JPEG, PNG, or WebP; maximum 8 MB</small>
</label>
<img id="cover-preview" class="cover-preview" alt="" hidden>
<label>your blurb <span class="optional">optional Markdown</span>
<textarea name="blurb" rows="10" maxlength="20000"></textarea>
</label>
</div>
<div id="writing-fields" hidden>
<label>description <span class="optional">optional</span>
<input name="description" type="text" maxlength="500" disabled>
<small>A short summary for search results and link previews.</small>
</label>
<label>your piece <span class="optional">Markdown</span>
<textarea name="body" rows="20" maxlength="200000" required disabled></textarea>
</label>
</div>
<button class="submit-btn" type="submit">commit entry</button>
</form>
<p id="form-status" class="form-status" role="status" aria-live="polite"></p>
</section>
"""
    dest = OUTPUT / "admin"
    dest.mkdir(parents=True, exist_ok=True)
    write_page(
        dest / "index.html",
        base_page(
            "add to site",
            body,
            active="collections",
            depth=1,
            robots="noindex, nofollow",
            scripts=("admin.js",),
        ),
    )


def build_cloudflare_files():
    headers = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), geolocation=(), microphone=()
  Content-Security-Policy: default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'
"""
    (OUTPUT / "_headers").write_text(headers, encoding="utf-8")
    routes = {"version": 1, "include": ["/admin/submit"], "exclude": []}
    (OUTPUT / "_routes.json").write_text(
        json.dumps(routes, indent=2) + "\n", encoding="utf-8"
    )


def copy_static():
    """Copy static files and create web-ready image derivatives."""
    for filename in ("style.css", "theme.js", "admin.js"):
        source = STATIC / filename
        if not source.exists():
            raise BuildError(f"missing required static asset: {source}")
        shutil.copy2(source, OUTPUT / filename)

    cover_manifest = {}
    cover_outputs = set()
    covers_src = STATIC / "covers"
    if covers_src.exists():
        for source in sorted(covers_src.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            relative = source.relative_to(covers_src)
            asset = optimize_image(
                source,
                OUTPUT / "covers" / relative.parent,
                max_edge=1200,
            )
            output_name = str(relative.parent / asset["filename"])
            key = relative.as_posix()
            if output_name in cover_outputs:
                raise BuildError(f"optimized cover filename collision: {source}")
            cover_outputs.add(output_name)
            cover_manifest[key] = asset

    image_manifest = {}
    image_outputs = set()
    images_src = STATIC / "images"
    if images_src.exists():
        for source in sorted(images_src.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            relative = source.relative_to(images_src)
            asset = optimize_image(
                source,
                OUTPUT / "images" / relative.parent,
                max_edge=2000,
                lossless=source.suffix.lower() == ".png",
            )
            output_name = str(relative.parent / asset["filename"])
            if output_name in image_outputs:
                raise BuildError(f"optimized image filename collision: {source}")
            image_outputs.add(output_name)
            asset["filename"] = output_name
            image_manifest[relative.as_posix()] = asset

    return cover_manifest, image_manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build():
    # Clean output
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()

    cover_manifest, image_manifest = copy_static()
    build_home(image_manifest)
    build_about(image_manifest)
    build_writing(image_manifest)
    build_collections(cover_manifest)
    build_admin()

    build_sitemap()
    build_robots()
    build_cloudflare_files()

    page_count = len(list(OUTPUT.rglob("*.html")))
    print(f"Built {page_count} pages → {OUTPUT}/")


if __name__ == "__main__":
    try:
        build()
    except BuildError as exc:
        raise SystemExit(f"Build failed: {exc}") from exc
