"""Claude client + DOM condenser (raw HTML bhejna token waste hai)."""
from __future__ import annotations

import json
import re
import anthropic

from config.settings import settings

_client = None


def claude() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY .env me set karo")
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def ask(system: str, user: str, max_tokens: int = 4000) -> str:
    resp = claude().messages.create(
        model=settings.AGENT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def ask_json(system: str, user: str, max_tokens: int = 4000):
    raw = ask(system + "\n\nRespond with ONLY valid JSON. No prose, no markdown fences.",
              user, max_tokens)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    return json.loads(cleaned)


DOM_JS = """
() => {
  const sel = 'input,select,textarea,button,a,[role],[data-testid],table,h1,h2,h3,label';
  return [...document.querySelectorAll(sel)].slice(0, 400).map(e => {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return null;
    return {
      tag: e.tagName.toLowerCase(),
      type: e.getAttribute('type') || undefined,
      id: e.id || undefined,
      name: e.getAttribute('name') || undefined,
      cls: (e.className && typeof e.className === 'string')
             ? e.className.split(/\\s+/).slice(0,4).join(' ') : undefined,
      testid: e.getAttribute('data-testid') || undefined,
      role: e.getAttribute('role') || undefined,
      placeholder: e.getAttribute('placeholder') || undefined,
      aria: e.getAttribute('aria-label') || undefined,
      text: (e.innerText || e.value || '').trim().slice(0, 60) || undefined,
    };
  }).filter(Boolean);
}
"""


def condense_dom(page) -> str:
    """Page ka interactive-element summary -- raw HTML se ~20x chhota."""
    els = page.evaluate(DOM_JS)
    return json.dumps({"url": page.url, "title": page.title(), "elements": els}, indent=1)
