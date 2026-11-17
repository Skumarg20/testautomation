"""
AI provider -- Gemini (free tier) ya Anthropic.

KYUN GEMINI
-----------
Anthropic ke credits khatam ho gaye the aur poora AI wala hissa band pad gaya.
Gemini ka free tier roz kaafi requests deta hai, aur saat tester roz chalayenge.

KYA AI KARTA HAI, KYA NAHI
--------------------------
AI sirf DO kaam karta hai, aur dono me uska jawab HUMESHA insaan ko dikhaya
jata hai -- chupchaap kabhi kuch save nahi hota:

  1. Jo line rule-parser samajh na paye, use steps me badalna
  2. Catalogue ke field ko aasan naam dena ("txtLedgerName27" -> "Party Name")

AI test CHALATA nahi hai. Chalane ka kaam poori tarah niyam-aadharit hai,
kyunki test ka matlab hi ye hai ki wo har baar bilkul ek jaisa chale. Agar
aaj AI ek step banaye aur kal doosra, to test bekaar ho jate hain.

DHYAAN
------
Free tier me bheja hua data provider ke paas jata hai. Isliye yahan sirf DOM
ke field ke naam jate hain -- password, GSTIN, ya kisi party ka data kabhi
nahi.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from config.settings import ROOT, settings

# AI key do jagah se aa sakti hai:
#   1. UI (Settings tab) -> config/ai.json      <- aam tareeka
#   2. .env                                      <- CI ya server ke liye
# UI wali pehle, taaki key badalne ke liye file kholni na pade.
KEY_FILE = ROOT / "config" / "ai.json"


def _saved() -> dict:
    if not KEY_FILE.exists():
        return {}
    try:
        return json.loads(KEY_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_key(provider: str, key: str, model: str = "") -> dict:
    """
    UI se AI key save karo.

    Model na diya ho (ya purana ho) to Google se live list lekar khud chun
    lete hain -- taaki tester ko model ke naam yaad na rakhne padein.
    """
    d = _saved()
    if provider == "gemini":
        d["gemini_key"] = key.strip()
        if model:
            d["gemini_model"] = model.strip()
        else:
            # "pick automatically" chuna gaya -- purana naam pehle HATAO.
            # Warna 'gemini-2.0-flash' jaisa hata hua naam file me pada
            # rehta hai aur 404 aata rehta hai, chahe user ne automatic
            # hi chuna ho.
            d.pop("gemini_model", None)
            try:
                best = pick_model(list_models(key.strip()))
                if best:
                    d["gemini_model"] = best
            except AIError:
                pass          # khali chhod do -- ask() pehli baar khud chun lega
    elif provider == "anthropic":
        d["anthropic_key"] = key.strip()
    else:
        raise AIError(f"'{provider}' naam ka koi provider nahi")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return {"provider": provider, "saved": True}


def gemini_key() -> str:
    return _saved().get("gemini_key") or settings.GEMINI_API_KEY


def gemini_model() -> str:
    """
    Abhi kaunsa model use ho raha hai.

    Kuch set na ho to khali lautate hain -- ask() us soorat me live list se
    chun leta hai. Yahan koi naam HARDCODE nahi karte, kyunki wahi galti
    404 le kar aayi thi.
    """
    return _saved().get("gemini_model") or settings.GEMINI_MODEL or ""


def anthropic_key() -> str:
    return _saved().get("anthropic_key") or settings.ANTHROPIC_API_KEY

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_URL = GEMINI_BASE + "/models/{model}:generateContent?key={key}"
GEMINI_LIST = GEMINI_BASE + "/models?key={key}&pageSize=100"


class NoProvider(RuntimeError):
    """Koi AI key set nahi hai."""


class AIError(RuntimeError):
    pass


class ModelGone(AIError):
    """Jo model likha tha wo Google ne hata diya."""


def available() -> dict:
    """Kaunsa provider chaalu hai."""
    g, a = bool(gemini_key()), bool(anthropic_key())
    return {"gemini": g, "anthropic": a, "model": gemini_model(),
            "from_ui": bool(_saved().get("gemini_key")
                            or _saved().get("anthropic_key")),
            "active": "gemini" if g else "anthropic" if a else None}


def list_models(key: str | None = None) -> list[str]:
    """
    Google se poochho ki abhi kaunse model chal rahe hain.

    Model ke naam code me likhna galat nikla: maine "gemini-2.0-flash" likha
    tha, aur Google ne use hata diya -- 404 aane laga. Naam badalte rehte
    hain, isliye live list hi sach hai.
    """
    k = key or gemini_key()
    if not k:
        raise NoProvider("Pehle Gemini key daalo")
    try:
        with urllib.request.urlopen(GEMINI_LIST.format(key=k), timeout=25) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        raise AIError(f"Model list nahi mili ({e.code}): {body}") from e
    except Exception as e:  # noqa: BLE001
        raise AIError(f"Google tak pahunch nahi paye: {e}") from e

    out = []
    for m in data.get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        name = (m.get("name") or "").split("/")[-1]
        if name:
            out.append(name)
    return out


def pick_model(models: list[str]) -> str | None:
    """
    List me se sabse theek model chuno.

    Pasand: flash (tez aur free tier me udaar) > lite > baaki.
    Preview/experimental aakhir me, kyunki wo bina bataye hat jate hain --
    theek wahi hua jo abhi "2.0-flash" ke saath hua.
    """
    if not models:
        return None

    def rank(m: str) -> tuple:
        low = m.lower()
        unstable = any(w in low for w in ("preview", "exp", "thinking"))
        family = 0 if "flash" in low and "lite" not in low else \
                 1 if "lite" in low else \
                 2 if "pro" in low else 3
        # naya version pehle: naam me sabse bada number
        nums = [float(x) for x in re.findall(r"(\d+\.?\d*)", low)] or [0]
        return (unstable, family, -max(nums), len(m))

    return sorted(models, key=rank)[0]


def _post(url: str, payload: dict, timeout: int = 45) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:400]
        if e.code == 429:
            raise AIError("Gemini ki free-tier limit aaj ke liye khatam. "
                          "Kal apne aap chalu ho jayegi.") from e
        if e.code in (401, 403):
            raise AIError("AI key galat ya band hai. Settings me dobara daalo.") from e
        if e.code == 404 and "model" in body.lower():
            raise ModelGone(
                f"'{gemini_model()}' ab Google ke paas nahi hai.\n"
                f"  Model ke naam badalte rehte hain. 'Refresh models' dabao --"
                f" abhi jo chal raha hai wahi chun liya jayega."
            ) from e
        raise AIError(f"AI ne mana kiya ({e.code}): {body}") from e
    except Exception as e:  # noqa: BLE001
        raise AIError(f"AI tak pahunch nahi paye: {e}") from e


# Kisi bhi asli kaam ki call itne token se kam na le.
#
# Do wajah:
#   1. Chhoti seema se jawab beech me kat jata hai, aur adhoora JSON bilkul
#      bekaar hota hai -- aadha step likha ho to wo galat step banata hai.
#   2. Naye model jawab likhne se PEHLE "sochte" hain. Hum thinkingBudget=0
#      se sochna band karte hain, par koi model wo setting na maane to soch
#      phir token khane lagegi. Us soorat me chhoti seema khali jawab degi --
#      theek wahi jo gemini-3.7-flash ke saath hua tha.
MIN_OUTPUT_TOKENS = 2048
PING_TOKENS = 256          # sirf "OK" chahiye, isliye chhota


class OutOfTokens(AIError):
    """Model ne jawab likhna shuru kiya hi nahi -- seema chhoti thi."""


def _gemini(system: str, user: str, max_tokens: int) -> str:
    model = gemini_model()
    if not model:
        # Pehli baar: Google se poochh kar chun lo aur yaad rakh lo
        model = pick_model(list_models()) or ""
        if not model:
            raise AIError("Koi model available nahi mila")
        d = _saved()
        d["gemini_model"] = model
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(json.dumps(d, indent=1), encoding="utf-8")
    url = GEMINI_URL.format(model=model, key=gemini_key())

    cfg = {
        # temperature 0 -- 0.1/0.2 NAHI.
        #
        # Test ka poora matlab ye hai ki wo har baar bilkul ek jaisa chale.
        # 0.1 par bhi model kabhi-kabhi alag step bana dega, aur do tester ko
        # ek hi line se do alag test milenge. Structured output me randomness
        # ka koi faayda nahi, sirf nuksaan hai.
        "temperature": 0,
        "maxOutputTokens": max(max_tokens, MIN_OUTPUT_TOKENS),
        # Naye Gemini model jawab likhne se PEHLE "sochne" me token kharch
        # karte hain. Humara kaam seedha hai (line -> steps), isliye sochna
        # band kar dete hain -- warna saare token soch me chale jate hain
        # aur jawab khali aata hai (finishReason: MAX_TOKENS, content: {}).
        "thinkingConfig": {"thinkingBudget": 0},
    }
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": cfg,
    }

    try:
        data = _post(url, body)
    except AIError as e:
        # Purane model thinkingConfig nahi samajhte -- uske bina dobara
        if "thinking" in str(e).lower() or "unknown name" in str(e).lower():
            cfg.pop("thinkingConfig", None)
            data = _post(url, body)
        else:
            raise

    text = _extract(data)
    reason_now = _finish_reason(data)
    if text and reason_now != "MAX_TOKENS":
        return text
    if text and reason_now == "MAX_TOKENS":
        # Jawab AAYA par beech me KAT gaya. Adhoora JSON parse to ho hi nahi
        # payega, aur agar ho gaya to aadhe step banenge -- jo chupchaap galat
        # test bana dega. Isliye ise kaamyabi nahi maanate.
        raise OutOfTokens(
            f"Jawab {max_tokens} token par beech me kat gaya (finishReason="
            f"MAX_TOKENS).\n  Adhoora jawab use karna khatarnak hai -- usse "
            f"aadhe step bante hain.\n  Model: {model}")

    # Khali jawab: aksar seema chhoti thi. Ek baar badi seema se dobara.
    reason = reason_now
    if reason == "MAX_TOKENS" and cfg["maxOutputTokens"] < 8192:
        cfg["maxOutputTokens"] = min(cfg["maxOutputTokens"] * 4, 8192)
        text = _extract(_post(url, body))
        if text:
            return text
        raise OutOfTokens(
            f"Model ne jawab likha hi nahi -- {cfg['maxOutputTokens']} token "
            f"ki seema me bhi.\n"
            f"  '{model}' ye token jawab likhne se pehle 'sochne' me kharch "
            f"kar raha hai.\n"
            f"  Settings me 'Refresh models' se koi doosra model chuno "
            f"(flash wale sabse theek rehte hain)."
        )

    raise AIError(f"Gemini ka jawab khali aaya (finishReason={reason or '?'}). "
                  f"Model: {model}")


def _finish_reason(data: dict) -> str:
    try:
        return (data.get("candidates") or [{}])[0].get("finishReason", "") or ""
    except Exception:  # noqa: BLE001
        return ""


def _extract(data: dict) -> str:
    """Jawab me se text nikaalo. Khali ho to khali string -- crash nahi."""
    try:
        parts = data["candidates"][0].get("content", {}).get("parts") or []
    except (KeyError, IndexError):
        return ""
    return "".join(p.get("text", "") for p in parts).strip()


def _anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_key())
    r = client.messages.create(model=settings.AGENT_MODEL, max_tokens=max_tokens,
                               system=system, temperature=0,
                               messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in r.content if b.type == "text")


def _forget_model():
    d = _saved()
    d.pop("gemini_model", None)
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(json.dumps(d, indent=1), encoding="utf-8")


def ask(system: str, user: str, max_tokens: int = MIN_OUTPUT_TOKENS,
        allow_small: bool = False) -> str:
    """
    allow_small=True sirf ping ke liye -- wahan sirf "OK" chahiye.
    Baaki har jagah seema MIN_OUTPUT_TOKENS se kam nahi hoti.
    """
    if not allow_small:
        max_tokens = max(max_tokens, MIN_OUTPUT_TOKENS)
    who = available()["active"]
    if who == "gemini":
        try:
            return _gemini(system, user, max_tokens)
        except ModelGone:
            # Model beech kaam me hat gaya. Naam bhool kar dobara chuno --
            # tester ko iska pata bhi nahi chalna chahiye.
            _forget_model()
            return _gemini(system, user, max_tokens)
    if who == "anthropic":
        return _anthropic(system, user, max_tokens)
    raise NoProvider(
        "Koi AI key set nahi hai. Settings me GEMINI_API_KEY daalo "
        "(free tier: aistudio.google.com/apikey)."
    )


JSON_RULE = (
    "\n\nOUTPUT RULES (follow exactly):\n"
    "- Return ONLY a strict JSON object. No prose, no markdown fence, no "
    "explanation before or after.\n"
    "- Keep it compact: no pretty-printing, no comments, no extra keys.\n"
    "- If you are unsure about a line, put it in \"unknown\" instead of "
    "guessing a step."
)


def ask_json(system: str, user: str, max_tokens: int = MIN_OUTPUT_TOKENS):
    raw = ask(system + JSON_RULE, user, max_tokens)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Adhoora JSON aksar kat-ne ki nishani hota hai
        if cleaned and not cleaned.rstrip().endswith(("}", "]")):
            raise OutOfTokens(
                "AI ka jawab beech me kat gaya -- JSON poora nahi aaya.\n"
                f"  Jitna aaya: ...{cleaned[-120:]}\n"
                "  Seema badha kar dobara koshish karo."
            ) from e
        raise AIError(f"AI ne JSON nahi diya: {cleaned[:200]}") from e


# ------------------------------------------------------------- kaam #1

# Prompt jitna chhota, jawab ke liye utne token bache.
# Pehla prompt lamba tha aur udaharan bhi dete the -- wo har call me token
# khata tha. Ab sirf niyam, aur woh bhi seedhe.
STEP_SYSTEM = """You convert a QA tester's plain sentences into test steps for
MargBooks (Indian billing software). Input may be English or Hinglish.

Allowed actions ONLY:
open_screen open_menu goto click fill select press wait_text assert_text
assert_no_text assert_visible sleep screenshot note set_party fill_header
add_item add_barcode pick_batch expect_lines expect_total expect_trade
expect_field expect_column set_bill_discount close_form save_form

Rules:
- "target" must come from the screens/fields list given below. Never invent one.
- A line you cannot map goes in "unknown". Never guess a step.
- add_item / add_barcode value format: "item or barcode | qty | rate"

JSON shape:
{"steps":[{"action":"","target":"","value":"","note":"original line"}],
"unknown":[{"line":"","why":""}],"module":""}"""


def text_to_steps(text: str, screens: list[str], fields: list[str]) -> dict:
    """Saadhi bhasha -> steps. Rule-parser jo na samjhe, uske liye."""
    # Sirf kaam ke fields bhejte hain, saare 200 nahi.
    # Har call me poori list bhejna token kharch karta tha aur jawab ke liye
    # kam bachta tha -- wahi MAX_TOKENS wali dikkat ki ek wajah thi.
    words = set(re.findall(r"[a-zA-Z_]{3,}", text.lower()))
    handy = [f for f in fields
             if any(w in f.lower() for w in words)] or list(fields)
    handy = sorted(set(handy))[:80]

    return ask_json(
        STEP_SYSTEM,
        f"screens: {sorted(screens)}\n"
        f"fields: {handy}\n\n"
        f"tester wrote:\n{text}",
        max_tokens=4000)


# ------------------------------------------------------------- kaam #2

NAME_SYSTEM = """Tum HTML field ko aasan naam dete ho, taaki QA tester unhe
apni bhasha me bula sake.

Har field ka aisa naam do jo screen par likha dikhta hai
(jaise "Party Name", "M.R.P", "Bill No."). Agar label maujood hai to wahi lo.
Label na ho to id/placeholder se andaza lagao, par aisa naam do jo insaan
padh sake -- "txtLedgerName27" nahi, "Party Name".

JSON do: {"names": {"<element key>": "<aasan naam>"}}"""


def name_fields(elements: list[dict]) -> dict:
    """
    Catalogue ke un fields ko naam do jinka label nahi mila.

    Sirf DOM ke naam bheje jate hain -- koi user data nahi.
    """
    slim = [{"key": e["key"], "id": e.get("id", ""),
             "placeholder": e.get("placeholder", ""),
             "kind": e.get("kind", "")}
            for e in elements if not e.get("label")][:60]
    if not slim:
        return {}
    return ask_json(NAME_SYSTEM, json.dumps(slim, ensure_ascii=False),
                    max_tokens=1500).get("names", {})



def check() -> dict:
    """
    Key sach me chal rahi hai? Ek chhota sawaal poochh kar dekhte hain.

    Sirf "key set hai" dikhana kaafi nahi -- galat key bhi set dikhti hai,
    aur pata tab chalta hai jab tester ke saamne fail hota hai.
    """
    who = available()["active"]
    if not who:
        return {"ok": False, "why": "Koi key set nahi hai"}
    try:
        # 10 token bahut kam the -- naye model utne to sochne me hi laga
        # dete hain aur jawab khali aata hai.
        out = ask("Reply with exactly: OK", "ping",
                  max_tokens=PING_TOKENS, allow_small=True)
        return {"ok": True, "provider": who, "model": gemini_model(),
                "reply": out.strip()[:40]}
    except ModelGone as e:
        # Model hat gaya -- live list se naya chun kar EK BAAR aur try karo.
        # Tester ko ye khud nahi karna chahiye.
        try:
            best = pick_model(list_models())
            if not best:
                return {"ok": False, "provider": who, "why": str(e)}
            d = _saved()
            d["gemini_model"] = best
            KEY_FILE.write_text(json.dumps(d, indent=1), encoding="utf-8")
            out = ask("Reply with exactly: OK", "ping",
                  max_tokens=PING_TOKENS, allow_small=True)
            return {"ok": True, "provider": who, "model": best,
                    "reply": out.strip()[:40],
                    "note": f"Purana model hat gaya tha -- ab '{best}' use ho raha hai"}
        except AIError as e2:
            return {"ok": False, "provider": who, "why": str(e2)}
    except AIError as e:
        return {"ok": False, "provider": who, "why": str(e)}
