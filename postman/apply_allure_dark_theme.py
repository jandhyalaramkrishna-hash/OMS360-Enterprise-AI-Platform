#!/usr/bin/env python3
"""
OMS-360 Enterprise QA - Apply dark theme as the Allure report's default.

Allure's report (this project uses allureVersion 2.43.0's newer bundled
UI) remembers the user's theme choice in the browser via
localStorage["allure-theme"] ("light"/"dark"), falling back to the OS
`prefers-color-scheme` media query when nothing is stored yet, and applies
it via a `data-theme` attribute on <html> (confirmed by reading the real
generated assets/index-*.js bundle, not guessed).

`allure generate --clean` regenerates `index.html` from scratch on every
run, so any manual edit to it is wiped out on the next pipeline run. This
script re-applies a small, idempotent snippet into the report's own
official customization slot every time, right after `allure generate`
succeeds:

    <!-- allure-core-head:start -->
    <!-- allure-core-head:end -->

On first-ever visit to the report in a given browser (no stored
preference yet), this makes it open in dark theme immediately - no
flash of light theme, and it never overrides a viewer's own later choice
(clicking the theme toggle updates localStorage, which this script's own
`if (!localStorage.getItem(...))` guard then respects on the next visit).

Exit code 0 on success. Exit code 1 if index.html is missing or doesn't
contain the expected marker comments (report structure changed - stop
rather than silently doing nothing).
"""
import argparse
import sys
from pathlib import Path

MARKER_START = "<!-- allure-core-head:start -->"
MARKER_END = "<!-- allure-core-head:end -->"

SNIPPET = """<!-- allure-core-head:start -->
<!-- OMS-360: default new visitors to dark theme, never overrides an explicit user choice -->
<script>
(function () {
    try {
        var stored = window.localStorage.getItem('allure-theme');
        if (stored !== 'light' && stored !== 'dark') {
            stored = 'dark';
            window.localStorage.setItem('allure-theme', 'dark');
        }
        document.documentElement.setAttribute('data-theme', stored);
    } catch (e) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
})();
</script>
<!-- allure-core-head:end -->"""


def main():
    parser = argparse.ArgumentParser(description="Apply dark-theme-by-default to a generated Allure report (idempotent).")
    parser.add_argument("--allure-report-dir", default="allure-report")
    args = parser.parse_args()

    index_path = Path(args.allure_report_dir) / "index.html"
    if not index_path.exists():
        print(f"[ERROR] {index_path} does not exist - run `allure generate` first.")
        sys.exit(1)

    html = index_path.read_text(encoding="utf-8")

    if MARKER_START not in html or MARKER_END not in html:
        print(f"[ERROR] {index_path} does not contain the expected "
              f"'{MARKER_START}' / '{MARKER_END}' markers - the Allure "
              f"report template may have changed. Not modifying the file.")
        sys.exit(1)

    start_idx = html.index(MARKER_START)
    end_idx = html.index(MARKER_END) + len(MARKER_END)
    new_html = html[:start_idx] + SNIPPET + html[end_idx:]

    if new_html == html and SNIPPET in html:
        print("[OK] Dark-theme-default snippet already present (idempotent no-op).")
    else:
        index_path.write_text(new_html, encoding="utf-8")
        print(f"[OK] Dark-theme-default snippet applied to {index_path}.")

    sys.exit(0)


if __name__ == "__main__":
    main()
