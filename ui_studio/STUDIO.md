# Test Studio

The new no-code UI for MargBooks QA, built from `Test_Studio_Mockup_final.html` and `IMPLEMENTATION_PROMPT.md`,
on top of this project. Start it with **`studio.bat`** → http://localhost:8778.
The old UI (`ui.bat`, port 8777) is unchanged and shares the same tests, environments and app memory.

```
Record (Playwright codegen) ─┐
                             ├─> script (.spec.ts text) -> Verify -> Confirm changes -> Replay -> AI auto-fix -> Save
Write (plain words)  ────────┘   (Write: lines -> Generate code)
```

## New tester PC

1. Copy the project folder (keep `.env`, `config/`, `testcases/saved/`). Run `setup.bat` once (creates `.venv`,
   installs libraries and `playwright install chromium`, which also installs the ffmpeg that video needs).
2. `studio.bat` → **Settings**: URL, user ID, password, company → **Save** → **Test login**.
3. Optional AI: set `GEMINI_API_KEY` in `.env` (or in the old UI → Settings → AI helper). Without a key every
   local feature works; AI suggestions and AI auto-fix say so and stay off.
4. **Learn app** (test company only: tick *This is a test company* in Settings first) → *Start learning*.
   Until this has run once, app memory is whatever the crawler already saved in `locators/locators_registry.json`.

## Where things are

| File | Job |
|---|---|
| `server.py` | HTTP ↔ JSON only (port 8778). Routes listed in `API.md`. |
| `app.html` | The UI: the mockup's CSS, markup and flow, simulation replaced by API calls. |
| `memory.py` | App memory built from the crawler's registry + `framework/screens.py` + taught words (`config/studio_aliases.json`). Stability score: formcontrolname > id > name > placeholder > position. |
| `grammar.py` | The step grammar, live check, palette, lines → YAML steps. 0 tokens. |
| `script.py` | lines → `.spec.ts`; `.spec.ts` → YAML steps (reuses `ui/codegen_import.py`); Chrome Recorder JSON. |
| `verify.py` | Local rules, AI only for what rules cannot judge. |
| `executor.py` | Replay, AI auto-fix loop, Run; the one browser function `_play`. |
| `recorder.py` | Starts codegen (argv list, no shell), follows its output file, redacts passwords. |
| `tests.py` | Save (YAML + `.spec.ts`), tests list, runs, report HTML, bug pack zip. |
| `learn.py`, `bulk.py`, `state.py` | Learn the app (wraps `ui/tools.py`), bulk bills, SQLite (`config/studio.db`) + settings JSON. |

Tests: `tests/unit/test_studio.py` (43, no browser), `tests/browser/test_studio_play.py` (2, local fake page).

## Mockup → implementation

| Mockup screen / control | Implemented in |
|---|---|
| Home: 4 start cards, KPIs, app-memory line, env pill | `app.html`; `GET /api/state` (`get_state`) |
| Record: start URL, *reuse saved login*, **Record automation case**, live action feed, **Stop**, editable code | `recorder.py`; `/api/record/start`, `/feed`, `/stop` |
| Feedback: *Report a problem* on the Run fail box, Reports drawer, a test case, a failed replay, a Verify suggestion, a ✗ line in Write, the login cards, and the global Feedback screen (admin: status + reply; QA: own). Live feedback on a test = ⚠ known issue | `feedback.py`; `/api/feedback`, `/api/feedback/update` (admin), `/api/feedback/known` |
| Login tests: tick *This test checks the login screen* (Record or Paste). The recorded login steps stay (wrong password, unknown user...); the script gets a `// studio: login test` line; the run starts with `sign_out` (this browser only) and the login page. A known password / user id becomes `process.env.MB_PASS!` / `MB_USER!` (`{{config_password}}` / `{{config_user}}` at run time). Saved with tags `login-test`, `breaks_session` | `script.is_login_test`, `recorder.redact_login_test`, step `sign_out` |
| Verify script, Confirm change / Skip / Confirm all | `verify.py`; `/api/verify`, `/api/verify/apply` |
| Replay, attempt counter, error box, **AI fix**, Try again, Bug pack | `executor.py` (`start_replay`, `ai_fix`, `diagnose`); `/api/replay`, `/status`, `/retry` |
| Save form (Module*, Priority, Test case*, Description, Written by*) | `tests.save`; `/api/save` → `testcases/saved/TC_nnn.yaml` + `<out dir>/<module>/tc-nnn-<slug>.spec.ts` |
| Write: name, module, author, Open, **+ New case** | `app.html`; `/api/tests`, `/api/tests/open` |
| Write: gutter ✓/✗, red lines, Live check (screen › field › locator › action › value), Insert chips | `grammar.check`; `/api/write/check` |
| Red line: **Use**, **Teach** | client + `/api/write/teach` (`memory.teach`, applies to everyone) |
| Red line: AI suggestion (~1 s after typing, only if no local one, cached, memory-validated) | `server.ai_suggest`; `/api/write/ai` |
| **Save draft**, **Generate code** (enabled only when every line is ✓) | `/api/tests/save-draft`; `/api/write/generate` |
| Run: module pills with counts, tests ticked, Select all, *Run N tests*, options, live steps, failure box | `executor.start_run`, `tests.load_cases`; `/api/run` |
| Reports: KPIs, runs table, drawer (steps, screenshots, files) | `tests.list_runs`, `run_detail`; `/api/runs`, `/api/runs/detail`, `/api/runs/file` |
| Downloads: video, `trace.zip`, Chrome Recorder JSON, spec, HTML report, bug pack | `/api/download?kind=…` (`server.download`, `tests.py`) |
| Learn: Walk the app (6 steps), **Restore settings**, Read the source code, Remembered fields table | `learn.py` over `ui/tools.py` (crawler `--enable`, `restore_settings`, `code_scanner`); `/api/learn/*`, `/api/code/read`, `/api/memory` |
| Settings: URL, user, password, company, business type, **Test login**, bulk rules, codegen command, output folder, AI mode, token limit, fix attempts | `/api/settings`, `/api/settings/test-login`; env fields go to `ui/envs.py`, the rest to `config/studio_settings.json` |

## Differences from the prompt and the mockup (the project's conventions win for code)

- **Stack.** The prompt asked for a Node/TypeScript agent and React. This project is Python and its UI is a single
  HTML file, so Studio is a stdlib Python server plus the mockup's single HTML file (no build step), like `ui/`.
- **Two files per test (your choice "Both").** The runnable source is the YAML. Replay and Run convert the script to
  YAML and run it with the project's own `StepRunner` (safety guard, netguard, Control Room checks, healing), not
  `npx playwright test`. The `.spec.ts` is an export for developers; it imports `../helpers/mb`, a helper module
  **this project does not have**, so the `.spec.ts` files are not runnable by this tool until someone writes it.
- **Password storage.** The prompt asked for the OS credential store. Not done: the password stays in
  `config/environments.json` (plain text, git-ignored), exactly as the old UI stores it. It is never sent to the
  browser, logged, written into scripts, reports or bug packs; recorded passwords are replaced by `process.env.MB_PASS`.
- **Token counts are estimates** (4 characters ≈ 1 token) because `framework/ai.py` does not return the provider's count.
- **Hinglish** lines are not in Studio's Write grammar (the old UI's `ui/nl.py` has them).
- **Business type override** is saved in Settings but the runner still auto-detects the trade.
- Added to Settings: *This is a test company* (Learn app and bulk bills refuse without it) and *Allow tests that
  create or change data*.
- Small backward-compatible edits to shared code: `framework/base_page.py` (a step target may be a real selector),
  `framework/step_runner.py` (`add_item` 4th part = discount, `press` without a target, `bulk_sale_bills`),
  `pages/sale_bill_page.py` (`discount` argument), `framework/data_factory.py` (`{{today}}`). The existing 305 unit tests still pass.

## Not done, or not verified here

Verified with tests: grammar, memory, script round trip, every verify rule, AI guard rails (limit, mode, cache,
memory check), the replay + AI-fix loop with the browser stubbed, the browser part against a local fake page
(per-step status and screenshots, trace, failing step), save, bug pack (no password), HTTP layer, and the UI driven in Edge.

**Not verified** (needs a live MargBooks company, a visible browser window or an AI key):
- a real Replay or Run on MargBooks, and AI auto-fix with a real model;
- Record with a real codegen window (command building, redaction and parsing are tested, the window is not);
- Learn the app: the six-step progress is inferred from keywords in the crawler's output, so it is approximate;
- **Test login**; video (needs ffmpeg from `playwright install`; Studio skips video and says so when it is missing);
- importing `recorder.json` into Chrome DevTools → Recorder (the shape follows the format, never imported);
- **Bulk bills** (`bulk.py`): written, never run; "Sundry Debtors only" and "in-stock only" are best-effort and it
  refuses unless *test company* is ticked;
- the Verify rule *field found by page position* maps a locator only when the script names the screen and a comment
  or AI identifies the field; otherwise it says "edit by hand";
- the written case's `.spec.ts` helpers (`../helpers/mb`), see above.
