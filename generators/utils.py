import yaml
import markdown


def parse_md_file(file_path, use_fenced_code=False):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

        _, front_matter, body = content.split("---", 2)
        metadata = yaml.safe_load(front_matter)

        extensions = []
        if use_fenced_code:
            extensions.append("fenced_code")

        html_content = markdown.markdown(body, extensions=extensions)

        return {**metadata, "content": html_content}
