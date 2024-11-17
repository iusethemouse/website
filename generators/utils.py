import yaml
import markdown


def parse_md_file(file_path):
    with open(file_path, "r") as f:
        content = f.read()
        _, front_matter, body = content.split("---", 2)
        metadata = yaml.safe_load(front_matter)
        html_content = markdown.markdown(body)
        return {**metadata, "content": html_content}
