"""Recording helpers: show the mouse in a video and keep a final screenshot of each test."""

import contextlib
from pathlib import Path

from playwright.sync_api import BrowserContext
from playwright.sync_api import Error as PlaywrightError

CURSOR_DOT_ID = "qa-cursor-dot"
CLICK_RING_ID = "qa-click-ring"
FINAL_SCREENSHOT = "final.png"
LOAD_WAIT_MS = 15_000

OVERLAY_SCRIPT = f"""
(() => {{
    const style = (el, css) => Object.assign(el.style, css);
    const make = (id, css) => {{
        const el = document.createElement('div');
        el.id = id;
        style(el, {{ position: 'fixed', pointerEvents: 'none', zIndex: 2147483647, ...css }});
        return el;
    }};
    const install = () => {{
        if (document.getElementById('{CURSOR_DOT_ID}')) return;
        const dot = make('{CURSOR_DOT_ID}', {{
            width: '16px', height: '16px', marginLeft: '-8px', marginTop: '-8px', borderRadius: '50%',
            background: 'rgba(230, 30, 30, 0.8)', border: '2px solid white', left: '-50px', top: '-50px',
        }});
        document.documentElement.appendChild(dot);
        document.addEventListener('mousemove', (e) => {{
            style(dot, {{ left: e.clientX + 'px', top: e.clientY + 'px' }});
        }}, true);
        document.addEventListener('mousedown', (e) => {{
            const ring = make('{CLICK_RING_ID}', {{
                width: '40px', height: '40px', marginLeft: '-20px', marginTop: '-20px', borderRadius: '50%',
                border: '4px solid rgb(230, 30, 30)', left: e.clientX + 'px', top: e.clientY + 'px',
            }});
            document.documentElement.appendChild(ring);
            setTimeout(() => ring.remove(), 1200);
        }}, true);
    }};
    if (document.documentElement) install();
    else document.addEventListener('DOMContentLoaded', install);
}})();
"""


def finish_recording(context: BrowserContext, folder: Path | None) -> None:
    """Saves the last page of `context` as a screenshot once it has loaded; then the video can be closed."""
    if folder is None or not context.pages:
        return
    folder.mkdir(parents=True, exist_ok=True)
    last_page = context.pages[-1]
    # The screenshot is a best-effort extra: a page that never loads must not fail the test it records.
    with contextlib.suppress(PlaywrightError):
        last_page.wait_for_load_state("load", timeout=LOAD_WAIT_MS)
        last_page.screenshot(path=str(folder / FINAL_SCREENSHOT))
