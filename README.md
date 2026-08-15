# web10-checker

Conformance checker for **[The Web 1.0 Specification (2026 Edition)](SPEC.md)**:
no scripts, no third parties, no cookies, no bloat. HTML and CSS only.

A conforming site needs no cookie banner, because there is nothing to consent
to. Faults are graded like the British driving test: majors and minors, grades
A–F, and grades A–C are a pass.

## Install

```sh
uv sync
```

## Usage

Check a live page:

```sh
uv run web10 https://example.com/
```

Spider a whole site (same-site links only — the checker never wanders off to
other domains, and never fetches third-party resources at all):

```sh
uv run web10 https://example.com/ --spider --max-pages 25
```

Check a local static site before deploying (any absolute `http(s)` reference
is treated as third-party):

```sh
uv run web10 ./public --spider
```

Report formats: `--format text` (default), `--format json`, or
`--format html` — the HTML report is itself script-free, third-party-free,
and set in system fonts, obviously. Write to a file with `-o report.html`.

Exit code is `0` for a pass (grade A–C), `1` for a fail (D or F), `2` if
nothing could be checked — so it drops straight into CI:

```sh
uv run web10 ./public --spider || echo "deploy blocked"
```

## What gets checked

See [SPEC.md](SPEC.md) for the full rules. In short — majors: JavaScript in
any form, third-party requests, cookies, total transfer over 2 MB, autoplaying
media. Minors: HTML hygiene (doctype, title, `lang`, charset, `alt` text),
web fonts, transfer over 512 KB, more than 20 requests, first-party iframes.
A site is graded by its worst page.

## Tests

```sh
uv run pytest
```
