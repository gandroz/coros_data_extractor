# COROS data extractor from Training Hub

I love my Coros watch and the training hub is very helpful, but I also like data and I want to do further analysis with my own data. Coros does not provide official API to access you data, however the training hub has a public API you can interact with.

This simple tool helps you extract some of your data. For example, I've used this tool to extract all my runs with a meaningful title, always the same training, so that I can track my performance over time. I was then able to see the impact of my training on my heart rate, which is very encouraging.

## Usage

### Data extraction

You first need to setup two environment variables

```bash
ACCOUNT="...@.."
PASSWORD="....."
```

Then the tool is very easy to use with those simple commands:

```python
from coros_data_extractor.data import CorosDataExtractor

extractor = CorosDataExtractor()
extractor.login(os.environ.get("ACCOUNT"), os.environ.get("PASSWORD"))
extractor.extract_data()
extractor.to_json()
```

And that's it ! You now have your extracted data in a JSON file.

### Data models

For a more user friendly manipulation of the data, extraction of the data results is represented by a [pydantic](https://docs.pydantic.dev/latest/) data model. The model is described in `coros_data_extractor.model` module, but essentially you will find a list of activities with the description of the activity, the laps, and the associated time series.

## Development setup (macOS / zsh)

This project uses PEP 621 metadata in `pyproject.toml` and relies on the `Makefile` for a
convenient developer workflow. The Makefile prefers `uv` for dependency management and will
attempt to install `uv` via pip if it's not available. The project uses `ruff` for linting and
formatting.

Recommended steps to get started locally:

1. Install pyenv and ensure your shell is configured to use it (homebrew or your preferred method).
2. From the repository root run:

```bash
# Run the project install. The Makefile will try to install 'uv' if missing and then run
# `uv install` (or `python -m uv install` if only the package is importable).
make install
```

If `uv` cannot be installed or verified, `make install` will exit with an error and print
instructions to install `uv` manually. After a successful `make install` you'll have the
development dependencies available and pre-commit hooks installed.

Formatting and linting

Use the Makefile targets to format or lint the project with `ruff`:

```bash
make format   # runs `ruff format .`
make lint     # runs `ruff check .`
```

Notes

- The install flow will try to use the `uv` CLI when available. If the CLI is not on PATH but
	the `uv` package is importable (pip-installed into the active Python), the Makefile runs
	`python -m uv install` as a fallback.
- The Makefile registers an IPython kernel named `coros_data_extractor` for notebooks.
- Pre-commit hooks are installed by `make install`.

