def generate_home(env, output_dir):
    template = env.get_template("home.html")
    output = template.render()

    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(output)
