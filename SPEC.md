# The Web 1.0 Specification (2026 Edition)

**Certified Web 1.0** is a conformance standard for websites that respect their
visitors: no scripts, no surveillance, no third parties, no bloat. HTML and CSS
only. A conforming site sets no cookies and sends nothing to third parties, so
it has no need for a cookie banner.

Conformance is assessed per page. Faults are classified as **major** or
**minor**: a major fault fails the page outright, minor faults accumulate.
A site's grade is the grade of its worst page.

## Major faults

Major faults are counted once per rule per page: having JavaScript is one
fault, however many scripts you have. Occurrences are listed in the report.

| ID    | Fault | Definition |
|-------|-------|------------|
| JS-01 | JavaScript | Any `<script>` element (inline or external), any `on*` event-handler attribute, any `javascript:` URL, or any `<link>` that preloads a script (`rel="modulepreload"`, or `rel="preload" as="script"`). |
| TP-01 | Third-party request | Any resource (stylesheet, image, font, media, frame, preload) referenced from outside the page's own site. Two hosts are the same site if they share a registrable domain (`www.example.com` and `images.example.com` are the same site; `example.com` and `cdn.example.net` are not). Discovered in HTML and in first-party CSS (`url()`, `@import`). |
| CK-01 | Cookies | Any `Set-Cookie` header on the page or on any first-party resource. |
| WT-01 | Excessive transfer | Total first-party transfer (page plus all first-party resources) exceeds **2 MB**. |
| AV-01 | Autoplay | Any `<video>` or `<audio>` element with the `autoplay` attribute. |

## Minor faults

Minor faults are counted per occurrence, capped at 3 per rule per page.

| ID    | Fault | Definition |
|-------|-------|------------|
| HY-01 | Missing doctype | No `<!DOCTYPE html>`. |
| HY-02 | Missing title | No `<title>`, or an empty one. |
| HY-03 | Missing language | No `lang` attribute on `<html>`. |
| HY-04 | Missing charset | No character-encoding declaration (`<meta charset>` or equivalent). |
| HY-05 | Missing alt text | An `<img>` without an `alt` attribute. |
| FT-01 | Web fonts | Any `@font-face` in first-party CSS. |
| WT-02 | Overweight | Total first-party transfer exceeds **512 KB**. |
| RQ-01 | Excessive requests | More than **20** resource requests for a single page. |
| FR-01 | First-party frame | An `<iframe>` pointing at the page's own origin. (Third-party frames are TP-01, which is major.) |

## Grades

| Grade | Criteria | Result |
|-------|----------|--------|
| A | No majors, no minors | Pass |
| B | No majors, 1–4 minors | Pass |
| C | No majors, 5–9 minors | Pass |
| D | Exactly 1 major, fewer than 10 minors | Fail |
| F | 2 or more majors, or 10 or more minors | Fail |

Grades A–C are a **pass** and may display the Certified Web 1.0 badge for the
year of certification. Grades D and F are a **fail**.

## Scope and method

- Conformance is testable externally: fetch the page, parse the HTML, fetch
  first-party CSS, and enumerate referenced resources. No script execution is
  required - which is rather the point.
- The checker never fetches third-party resources; their presence alone is the
  fault. Transfer weight therefore counts first-party bytes only, measured
  uncompressed (what the browser must actually process).
- Media files on `<video>` or `<audio>` elements marked `preload="none"` are
  exempt from transfer weight: they are fetched only when a visitor chooses to
  play them, so a conforming page may host large media. They still count as
  requests, and posters (which load eagerly) still count as weight.
- `<noscript>` content is ignored (it is what a conforming visitor sees anyway).
- When checking a local directory before deployment, any absolute `http(s)`
  reference is treated as third-party.

## Versioning

This is the **2026 Edition**. The badge shows the year it was earned, and a
certification applies to that year only. Substantive rule changes require a
new edition.
