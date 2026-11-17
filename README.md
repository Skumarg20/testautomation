# MargBooks QA Agent

MargBooks (Marg ERP ka cloud accounting/billing/inventory product) ke liye ek
testing setup — test case library + Playwright automation + upar ek AI layer.
Goal: koi bhi banda repo clone karke **ek command** se MargBooks test kar sake.

```
./run.sh smoke
```

---

## Architecture

Teen layers, aur teeno ek doosre ko feed karti hain:

```
   testcases/*.yaml          <-- human-readable test case library (single source of truth)
          |
          v
   framework/                <-- Playwright runner: YAML padho, browser chalao, assert karo
   locators/margbooks.yaml   <-- logical key -> selector map (self-healing)
          |
          v
   agent/                    <-- AI layer
     discover.py   : live app dekh kar locators khud map karta hai
     generate.py   : screen dekh kar naye YAML test cases likhta hai
     explore.py    : khud browse karke bugs dhoondta hai
     triage.py     : failures ko REAL_BUG / LOCATOR_DRIFT / TEST_DATA / ENV / FLAKY me baantta hai
```

**Sabse important design choice:** naya test add karne ke liye Python likhna zaroori
nahi. `testcases/` me ek YAML block add karo, bas. Isliye manual QA wale log bhi
suite grow kar sakte hain, aur AI agent bhi wahi format likhta hai jo insaan likhta hai.

---

## Setup

**Windows walon ke liye:** `setup.bat` -> `doctor.bat` -> **`ui.bat`**.
`ui.bat` browser me ek page kholta hai jahan test chun kar chalaye ja sakte hain,
naye test likhe ja sakte hain, aur Excel se import ho sakta hai.
Details `START-HERE.txt` me.

```bash
git clone <repo> && cd margbooks-qa-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env      # apna demo login aur ANTHROPIC_API_KEY bharo
```

`.env` me do cheezein dhyaan se:

| Key | Kya karta hai |
|---|---|
| `ALLOW_DESTRUCTIVE` | `false` rakho jab tak pakka na ho ki demo account hai. `false` pe wo saare tests skip ho jayenge jo data create/edit/delete karte hain. |
| `HEADLESS` | `false` karo jab debug karna ho — browser dikhega. |

---

## Pehli baar chalane ka order

Locators seed file me abhi *guesses* hain, kyunki MargBooks ka actual DOM repo me
hardcode nahi kiya gaya. Isliye pehle discovery chalao:

```bash
# 1. AI agent live app pe jaake real selectors map karega
python -m agent.discover --all

# 2. Suite khud healthy hai ya nahi (browser ke bina chalta hai)
pytest tests/test_meta.py

# 3. Smoke suite
./run.sh smoke

# 4. Jo fail hua uska AI triage
./run.sh triage
```

Discovery ke baad `locators/margbooks.yaml` review zaroor karo — jo keys `MISS`
mark hui hain unhe manually bharna padega.

---

## Rozana ka use

```bash
./run.sh smoke                  # ~5 min, critical path
./run.sh safe                   # sab kuch except data-writing tests
./run.sh regression             # poora suite
pytest -m "sales and p1"        # module + priority filter
pytest --case TC_SALE_002       # ek hi case
pytest --tags gst,calculation   # tag filter
pytest -n 4                     # parallel
HEADLESS=false SLOWMO_MS=300 pytest --case TC_SALE_001   # debug
```

Har run ke baad `artifacts/` me: `report.html`, `results.json`, `trace.zip`,
failure screenshots, video. Trace kholne ke liye:
`playwright show-trace artifacts/trace.zip`

---

## AI layer kaise use karein

**Naye test cases likhwana:**
```bash
python -m agent.generate --page sale --url /sale/invoice --count 8
python -m agent.generate --page party --focus "GSTIN validation edge cases"
```
Output `testcases/9_generated_*.yaml` me jaata hai. **Review karke hi merge karo** —
AI-generated cases me kabhi-kabhi galat expectation hoti hai.

**Exploratory testing (bug hunting):**
```bash
python -m agent.explore --start /sale/invoice --steps 25
```
Read-only by default. Findings `artifacts/exploration.json` me. Jo finding valid
lage usko `generate` se permanent test case bana lo.

**Failure triage:**
```bash
./run.sh triage
```
40 red tests me se batata hai ki asli bug kaun se 3 hain aur baaki locator drift
ya stale data hai.

---

## Naya test case likhna (manual)

`testcases/03_sales.yaml` me append karo:

```yaml
- id: TC_SALE_006
  module: sales
  title: Round-off ke baad grand total nearest rupee pe aana chahiye
  priority: p2
  tags: [calculation]
  destructive: true
  expected: ["1234.56 -> 1235 dikhe aur round-off line 0.44 ho"]
  steps:
    - action: click
      target: nav.sales_menu
    - action: fill
      target: sale.rate
      value: "1046.23"
    - action: assert_text
      value: "Round"
```

- `target` hamesha `page.element` format me, aur locators file me exist karna chahiye
  (`tests/test_meta.py` ye enforce karta hai).
- `value` me placeholders: `{{item_name}} {{party_name}} {{gstin}} {{invalid_gstin}}
  {{batch_no}} {{hsn}} {{mobile}} {{qty}} {{rate}} {{gst_rate}}`
- `save_as: foo` se value store karo, baad me `{ctx.foo}` se use karo.
- Actions: `goto click fill select press wait_text assert_text assert_no_text
  assert_visible assert_not_visible sleep screenshot note`

---

## Abhi ki coverage (19 cases)

| Module | Cases | Kya cover hai |
|---|---|---|
| auth | 3 | valid login, wrong password, blank validation |
| masters | 5 | item create, party + GSTIN, invalid GSTIN, duplicate |
| sales | 5 | cash invoice, CGST/SGST vs IGST, zero qty, discount-before-tax |
| purchase/inventory | 3 | purchase se stock badhna, negative stock, expired batch |
| gst/reports | 3 | GSTR-1 generate, B2B reconciliation, future date empty state |

Sabse zyada value in gaps me hai — inhe next add karo: e-invoice IRN generation,
e-way bill, multi-godown transfer, credit note flow, user rights matrix,
opening balance carry-forward, aur invoice print template.

---

## Safety notes

- **Live account pe kabhi `ALLOW_DESTRUCTIVE=true` mat karo.** Suite fake invoices
  aur parties banati hai; wo live books me chali jayengi.
- Suite ka banaya har record `QA_` prefix se start hota hai (`config.settings.DATA_PREFIX`),
  taki demo account me pehchana aur clean kiya ja sake.
- `.env` `.gitignore` me hai. Credentials CI me GitHub Secrets se aate hain.
- `agent/explore.py` ek LLM ko browser control deta hai — isliye wo default me
  save/submit/delete nahi chhoo sakta.

## CI

`.github/workflows/qa.yml` roz 7 AM IST pe suite chalata hai, phir AI triage,
phir artifacts upload. Secrets set karne padenge: `MARGBOOKS_URL`, `MARGBOOKS_USER`,
`MARGBOOKS_PASS`, `ANTHROPIC_API_KEY`.
