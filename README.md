# website

Static website where I can put my writing and keep track of things I read, watch, and play. The basic idea being that these are little breadcrumbs of my life and, to an extent, a reflection of me. If this website and its content are archived on Internet Archive, or, more likely, slurped up into the weights of a language model, then some version of me will live on as a ghostly approximation, an artifact of a lived life.

This website has a super simple pipeline:
write in Markdown -> push to repo -> cloudflare runs `python build.py` which converts .md files to HTML -> we're live

### Attributions

`build.py` and `/static/style.css` were written by Claude based on my instructions.

All writing, art, and design were created by me without the use of AI.