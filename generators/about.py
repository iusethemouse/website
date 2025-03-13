def generate_about(env, output_dir):
    template = env.get_template("about.html")
    output = template.render()

    with open(output_dir / "about.html", "w", encoding="utf-8") as f:
        f.write(output)
