# Test Studio – API contract (ui_studio/server.py, port 8778)

All bodies and replies are JSON unless stated. Errors: `{"error": "plain words"}` with HTTP 400/404.
The UI is the single file `ui_studio/app.html`; it is the mockup `Test_Studio_Mockup_final.html`
with the simulated logic replaced by calls to this API. Layout, CSS, wording and flow stay the same.

## Pipeline (same for Record and Write)

```
Record (codegen)  ─┐
                   ├─> script (.spec.ts text) -> Verify -> Confirm changes -> Replay -> AI auto-fix -> Save
Write (plain text)─┘   (Write: lines -> Generate code)
```

The script text is the working artifact. The runner is the project's existing YAML step runner
(`framework/step_runner.py`), so Replay converts the script to YAML steps (`script_steps.py`),
runs them, and Save writes BOTH `testcases/saved/<id>.yaml` and `<tests dir>/<module>/tc-nnn-slug.spec.ts`.

## Endpoints

### GET /api/state
```
{ "env": {"name","app_url","company","user"}, "trade": "Pharma Agent"|"",
  "modules": ["Sale",...], "users": ["Ajay Rai",...],
  "ai": {"provider","active":bool,"mode":"local_first|always|never","limit":200000,"used":41200},
  "memory": {"learned_on":"13-Nov-2026"|null,"screens":N,"fields":N,"trade":"..."},
  "kpis": {"tests":N,"testers":N,"runs":N,"pass_rate":N|null},
  "allow_writes": bool }
```

### Settings
- `GET /api/settings` -> `{url,login_url,user,has_password,company,trade_mode,trade_options:[...],
   bulk:{party,item,batch,qty,shot}, codegen_cmd, out_dir, ai_mode, token_limit, fix_attempts, allow_writes, test_company:bool}`  (never the password)
- `POST /api/settings` same fields (+`password` only when changed) -> `{ok:true}`
- `POST /api/settings/test-login` -> `{ok:bool, message}` (runs `framework.auth` as a subprocess, 60 s)

### Memory ("Learn the app")
- `GET /api/memory?screen=&q=` -> `{"screens":["Sale Bill",...],"rows":[{"screen","field","kind","stab":0-100,
   "loc":{"primary":"[formcontrolname=\"x\"]","fcn","id","css","xpath"},"aliases":[...],"taught":[...]}], "total":N}`
- `POST /api/learn/start` `{}` -> `{job}`; `GET /api/learn/status?job=&since=N` ->
  `{"state":"running|done|failed","steps":[{"k":"login|trade|backup|cr|menu|crawl","state":"todo|doing|done","hint":"..."}],
   "log":"text since N","next":N}`
- `POST /api/learn/restore` -> `{job}` (same status endpoint)
- `POST /api/code/read` `{web, api}` -> `{ok, message, elements, routes}`

### Write
- `POST /api/write/check` `{lines:[...]}` ->
  `{"results":[Line,...], "ok":N, "bad":N, "palette":["Log in",...], "screen":"Sale Bill"|null}`
  Line = `{"status":"ok|bad|note|empty","kind":"login|open|pick|search|item|fill|click|verify|wait|bulk",
  "screen","route","note","why","term","fixes":["Field name"],"sugg":["Open Sale Bill"],"ai":bool,
  "field":Field|null,"value","qty","extras":[{"field":Field,"value"}],"what","secs","count","items","learned":bool}`
  Field = `{"name","sel","xpath","kind","stab"}`.  Free, local, 0 tokens. Call debounced on every edit.
- `POST /api/write/ai` `{line,screen}` -> `{"ok":true,"rewrite":"Set Rate to 50","tokens":N,"cached":bool}` or
  `{"ok":false,"msg":"AI could not map this line..."}`. Only when no local suggestion; answer already checked against memory.
- `POST /api/write/teach` `{term,screen,field}` -> `{ok:true}` (applies to everybody)
- `POST /api/write/generate` `{name,module,author,lines}` -> `{"code":"...","actions":N,"file":"written.spec.ts"}`
  Refuses (400) when any line is red.

### Record
- `POST /api/record/start` `{url, reuse_login:bool}` -> `{"session":"abc","command":"npx/py ..."}`
- `GET /api/record/feed?session=&since=N` -> `{"state":"recording|stopped|failed","actions":[{"n":1,"text":"Clicked User ID"}],"next":N,"message"}`
- `POST /api/record/stop` `{session}` -> `{"code":"...","actions":N}`

### Verify / Replay / Save (shared)
- `POST /api/verify` `{code, src:"record|written"}` ->
  `{"findings":[{"id","sev":"Must fix|Should fix|Nice to have","src":"Local check|Project rules|App memory|AI",
  "tokens":N,"title","why","old":["line"],"neu":["line"]}],"tokens":{"local":N,"ai":N}}`
- `POST /api/verify/apply` `{code, ids:[...]}` -> `{"code":"..."}`  (ids applied in order; "Skip" is client-side)
- `POST /api/replay` `{code, name, module, author}` -> `{"job":"r1"}`
- `GET /api/replay/status?job=` ->
  `{"state":"queued|running|fixing|passed|failed","attempt":1,"max":3,"aiFixes":0,
    "steps":[{"text","status":"todo|doing|ok|bad|skip","secs"}],
    "err":null|{"plain","err","lineText","fixText"},"code":"(current code, changes when AI fixed it)",
    "fixedLines":["..."],"tokens":{"local":N,"ai":N},"giveUp":bool,"log":"..."}`
- `POST /api/replay/retry` `{job}` -> same as replay
- `POST /api/save` `{code, name, module, priority, description, author, source:"record|written", lines?:[...]}` ->
  `{"id":"TC-006","yaml":"path","spec":"path"}`  (module, name, author required)

### Tests, Run, Reports
- `GET /api/tests` -> `{"tests":[{"id","name","module","author","date","type":"written|recorded|builtin","steps":N,"bad":N,"lines":[...]|null,"editable":bool}]}`
- `GET /api/tests/open?id=` -> `{"id","name","module","author","lines":[...],"code"}`  (written cases reopen in Write)
- `POST /api/tests/save-draft` `{id|null,name,module,author,lines}` -> `{"id"}`
- `POST /api/run` `{ids,video,shots,bugpack,stop_first}` -> `{"run_id"}`
- `GET /api/run?id=` -> `{"state","title","total","done","steps":[{"text","status","secs"}],"current":{"id","name"},
   "results":[{"test","result","passed","total","err","failAt"}],"seconds"}`
- `GET /api/runs` -> `{"runs":[{"id","test","name","module","author","at","passed","total","result","err","failAt"}],
   "kpis":{"runs","passed","failed","testers"}}`
- `GET /api/runs/detail?id=` -> `{"run":{...},"steps":[{"text","status"}],"files":{"video":bool,"trace":bool,"screens":[{"name","url"}]}}`
- Downloads (raw files, `Content-Disposition: attachment`):
  `GET /api/download?kind=recorder|spec|report|trace|video|bugpack&id=<run or test id>`

### Misc
- `GET /api/tokens` -> `{"month":N,"limit":N,"by_feature":{...}}`

## Additions made while building the backend

- Verify findings may carry `"manual": true`: the rule found a problem but has no safe automatic replacement
  (Confirm change does nothing; the tester edits the line). Also top-level `"ai_note"` when AI was skipped, with the reason.
- `GET /api/runs/file?id=<run>&name=<png>` serves a run's screenshot (the `url` in `/api/runs/detail`).
- `GET /api/run` on a run that could not start returns `"state":"error"` and the reason in `"title"` / `"log"`.
- Unknown API paths return JSON `{"error":"not found"}` with 404.
- Settings `trade_options` is a list of `{value,label}`; `trade_mode` is stored but the runner still auto-detects the trade.
