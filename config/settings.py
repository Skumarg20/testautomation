"""Central config. Everything comes from .env so no secret is ever in git."""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


# Comment tabhi mana jayega jab uske PEHLE space ho.
# Ye zaroori hai: "https://x.com" me bhi "//" hota hai. Pehle maine bina space
# ke bhi "//" ko comment maan liya tha aur poora URL kat kar "https:" reh gaya.
_COMMENT = re.compile(r"\s+(?:#|<-|//|;).*$")


def _clean(raw: str) -> str:
    """
    .env se aayi value saaf karo.

    Log aksar comment bhi copy kar lete hain:
        BROWSER_MAXIMIZE=true      <- default
    Aisi value "true" ke barabar nahi hoti aur setting chupchaap ULTI chal
    jaati hai -- jo sabse khatarnak bug hai kyunki error nahi aata.

    Par saavdhani: URL ko kaatna nahi hai. Isliye comment tabhi jab space ho.
    """
    if raw is None:
        return ""
    v = _COMMENT.sub("", str(raw).strip())
    return v.strip().strip('"').strip("'").strip()


def _bool(key: str, default: bool = False) -> bool:
    v = _clean(os.getenv(key, str(default))).lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return default          # kuch ajeeb likha ho to default, ulta nahi


def _int(key: str, default: int) -> int:
    try:
        return int(_clean(os.getenv(key, str(default))))
    except (ValueError, TypeError):
        return default


def _str(key: str, default: str = "") -> str:
    """Text values ke quotes/space hatao -- password ko haath nahi lagate."""
    return _clean(os.getenv(key, default))


class Settings:
    # Har zip ka apna build number. Ye purani files pakadne ke liye hai --
    # do baar aisa hua ki purana code chal raha tha aur pata hi nahi chala,
    # kyunki error dekhne me bilkul waisa hi lagta tha.
    BUILD = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() \
        else "unknown"

    # MargBooks do alag domains use karta hai:
    #   accounts.margbooks.com -> login
    #   books<N>.margbooks.com -> actual app (N account ke hisaab se badalta hai)
    LOGIN_URL = _str("MARGBOOKS_LOGIN_URL", "https://accounts.margbooks.com").rstrip("/")
    BASE_URL = _str("MARGBOOKS_APP_URL", "https://books5.margbooks.com").rstrip("/")

    USER = _str("MARGBOOKS_USER")
    PASSWORD = os.getenv("MARGBOOKS_PASS", "")
    PIN = _str("MARGBOOKS_PIN")
    COMPANY = os.getenv("MARGBOOKS_COMPANY", "")

    ALLOW_DESTRUCTIVE = _bool("ALLOW_DESTRUCTIVE", False)
    # false = har baar fresh login karo, saved session bilkul mat use karo
    USE_SAVED_SESSION = _bool("USE_SAVED_SESSION", False)

    HEADLESS = _bool("HEADLESS", True)
    # true = screen jitni badi ho utni window (dekhne ke liye best)
    # false = neeche wala pakka size (CI / repeatable tests ke liye)
    BROWSER_MAXIMIZE = _bool("BROWSER_MAXIMIZE", True)
    VIEWPORT_W = _int("VIEWPORT_W", 1440)
    VIEWPORT_H = _int("VIEWPORT_H", 900)
    SLOWMO_MS = _int("SLOWMO_MS", 0)
    TIMEOUT = _int("DEFAULT_TIMEOUT_MS", 20000)

    # AI: Gemini pehle (free tier hai), Anthropic backup
    GEMINI_API_KEY = _str("GEMINI_API_KEY")
    GEMINI_MODEL = _str("GEMINI_MODEL")   # khali = live list se chuna jayega
    ANTHROPIC_API_KEY = _str("ANTHROPIC_API_KEY")
    AGENT_MODEL = _str("AGENT_MODEL", "claude-sonnet-4-6")

    # Har run ka apna folder: artifacts/run_2026-08-22_21-30-15/
    # Isse pichhle run ke screenshots/report mite nahi.
    RUN_ID = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ARTIFACTS_ROOT = ROOT / "artifacts"
    ARTIFACTS = ARTIFACTS_ROOT / f"run_{RUN_ID}"
    TESTCASES = ROOT / "testcases"
    LOCATOR_FILE = ROOT / "locators" / "margbooks.yaml"
    STORAGE_STATE = ROOT / "storage_state.json"

    DATA_PREFIX = "QA_"

    @classmethod
    def init_run(cls, label: str = ""):
        """Run folder banao aur 'latest' pointer update karo."""
        cls.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        if label:
            (cls.ARTIFACTS / "_what.txt").write_text(
                f"{label}\nstarted: {cls.RUN_ID}\n", encoding="utf-8")
        (cls.ARTIFACTS_ROOT / "LATEST.txt").write_text(
            f"Sabse naya run:\n  {cls.ARTIFACTS.name}\n\n"
            f"Poora rasta:\n  {cls.ARTIFACTS}\n", encoding="utf-8")
        cls._prune()
        return cls.ARTIFACTS

    @classmethod
    def _prune(cls, keep: int = 20):
        """Sirf aakhri 20 run rakho, purane apne aap hat jayein."""
        try:
            runs = sorted([d for d in cls.ARTIFACTS_ROOT.glob("run_*") if d.is_dir()])
            import shutil
            for old in runs[:-keep]:
                shutil.rmtree(old, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

    @classmethod
    def validate(cls):
        # URL sach me URL hai? (ek baar comment-stripping ne
        # "https://accounts.margbooks.com" ko "https:" kar diya tha,
        # aur pata browser khulne ke baad chala.)
        for name, url in (("MARGBOOKS_LOGIN_URL", cls.LOGIN_URL),
                          ("MARGBOOKS_APP_URL", cls.BASE_URL)):
            if not url.startswith(("http://", "https://")) or "." not in url:
                raise RuntimeError(
                    f"{name} theek nahi lag raha: {url!r}\n"
                    f"  .env me pura URL hona chahiye, jaise https://books5.margbooks.com\n"
                    f"  (value ke saath comment mat likhna)"
                )
        if not cls.USER:
            raise RuntimeError("MARGBOOKS_USER .env me set karo")
        if not (cls.PASSWORD or cls.PIN):
            raise RuntimeError("MARGBOOKS_PASS ya MARGBOOKS_PIN me se ek zaroori hai")


def _apply_active_environment(path=None):
    """
    UI me chuna hua environment yahin lag jaye -- HAR entry point ke liye.

    Pehle ye sirf ui/runner me lagta tha. Isliye control-room.bat, login.bat,
    pom-check.bat waghairah seedha .env padh rahe the aur GALAT COMPANY khol
    dete the -- jabki UI me doosri company chuni hui thi.

    Ise settings ke andar rakha hai (ui me nahi) taaki koi bhi command isse
    bhool na sake.
    """
    f = Path(path) if path else (ROOT / "config" / "environments.json")
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        env = (d.get("envs") or {}).get(d.get("active"))
    except Exception:  # noqa: BLE001
        return None
    if not env:
        return None

    # Value CLASS aur INSTANCE dono par set karte hain.
    #
    # Sirf class par set karna khatarnak nikla: kisi ne agar instance par
    # koi value rakh di (test, ya koi purana code), to wo class wali value ko
    # DHAK deti hai -- aur environment chupchaap nazarandaz ho jata hai.
    # Aisa bug dikhta nahi, bas galat company khul jaati hai.
    targets = [Settings]
    inst = globals().get("settings")
    if inst is not None:
        targets.append(inst)

    def put(name, value):
        for t in targets:
            setattr(t, name, value)

    if env.get("login_url"):
        put("LOGIN_URL", env["login_url"].rstrip("/"))
    if env.get("app_url"):
        put("BASE_URL", env["app_url"].rstrip("/"))
    # A Test Studio server run uses the MargBooks login of the QA who started it (set in this process's
    # environment by ui_studio.worker), not the shared one in environments.json.
    own = os.environ.get("STUDIO_RUN_CREDS") == "1"
    if own:
        put("USER", os.environ.get("MARGBOOKS_USER", ""))
        put("PASSWORD", os.environ.get("MARGBOOKS_PASS", ""))
    if env.get("user") and not own:
        put("USER", env["user"])
    if env.get("password") and not own:
        put("PASSWORD", env["password"])
    if env.get("company"):
        put("COMPANY", env["company"])
    put("ALLOW_DESTRUCTIVE", bool(env.get("allow_writes")))
    put("ACTIVE_ENV", d.get("active"))
    return d.get("active")


settings = Settings()
Settings.ACTIVE_ENV = None
_apply_active_environment()
