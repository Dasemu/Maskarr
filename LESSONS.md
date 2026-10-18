# LESSONS.md

Recurring mistakes and how to avoid them. Read before starting work; add an entry when a mistake repeats.

## No linter or test suite configured
There is no `ruff`/`black`/`flake8`/`pytest` configuration in this repo. Don't assume a `lint`/`test` command exists — the closest available quick check is `python3 -m py_compile maskarr.py`.
