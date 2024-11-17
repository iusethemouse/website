def generate_home(env, output_dir):
    template = env.get_template("home.html")
    output = template.render()

    with open(f"{output_dir}/index.html", "w") as f:
        f.write(output)
