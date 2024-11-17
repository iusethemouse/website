from pathlib import Path
from .utils import parse_md_file


def generate_watching(env, output_dir, content_dir):
    template = env.get_template("watching.html")
    base_dir = Path(content_dir) / "watching"

    current_movies = []
    current_shows = []
    later_movies = []
    later_shows = []
    watched_movies = []
    watched_shows = []

    def process_media_files(directory, movies_list, shows_list):
        if directory.exists():
            for file in directory.glob("*.md"):
                media = parse_md_file(file)
                if media.get("type") == "movie":
                    movies_list.append(media)
                elif media.get("type") == "show":
                    shows_list.append(media)

    process_media_files(base_dir / "now", current_movies, current_shows)

    process_media_files(base_dir / "later", later_movies, later_shows)

    process_media_files(base_dir / "watched", watched_movies, watched_shows)

    # Sort movies and tv shows maybe ??
    watched_movies.sort(key=lambda x: x.get("date_watched", ""), reverse=True)
    watched_shows.sort(key=lambda x: x.get("date_finished", ""), reverse=True)

    output = template.render(
        current_movies=current_movies,
        current_shows=current_shows,
        later_movies=later_movies,
        later_shows=later_shows,
        watched_movies=watched_movies,
        watched_shows=watched_shows,
    )

    with open(f"{output_dir}/watching.html", "w") as f:
        f.write(output)
