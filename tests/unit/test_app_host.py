"""
Login ke baad app ka asli host pakadna -- browser ke bina test.

ASLI BUG: .env me books5 tha, company books4 pe khulti thi. Crawler har page
ke baad bp.goto("/dashboard") karta tha, jo books5 pe jaata tha (wahan session
nahi), Sign In page aata tha, aur crawler "app mar gayi" samajh ke dobara login
karta rehta tha.
"""
import pytest

from config.settings import Settings, settings
from framework import auth


class FakePage:
    def __init__(self, url):
        self.url = url


@pytest.fixture(autouse=True)
def _restore(monkeypatch):
    monkeypatch.setattr(Settings, "BASE_URL", "https://books5.margbooks.com")
    monkeypatch.setattr(settings, "BASE_URL", "https://books5.margbooks.com", raising=False)
    monkeypatch.setattr(Settings, "LOGIN_URL", "https://accounts.margbooks.com")
    monkeypatch.setattr(settings, "LOGIN_URL", "https://accounts.margbooks.com", raising=False)


def test_asli_host_alag_ho_to_BASE_URL_badal_jata_hai():
    new = auth.sync_app_host(FakePage("https://books4.margbooks.com/dashboard"))
    assert new == "https://books4.margbooks.com"
    assert settings.BASE_URL == "https://books4.margbooks.com"
    assert Settings.BASE_URL == "https://books4.margbooks.com", \
        "class par bhi lagna chahiye, warna naya Settings purani value dega"


def test_goto_ab_asli_host_par_jata_hai():
    """bp.goto('/dashboard') ka URL BASE_URL se bante hai -- wahi badalna tha."""
    auth.sync_app_host(FakePage("https://books4.margbooks.com/mstr/margsetup-controlroom"))
    path = "/dashboard"
    assert f"{settings.BASE_URL}{path}" == "https://books4.margbooks.com/dashboard"


def test_host_wahi_ho_to_kuch_nahi_badalta():
    assert auth.sync_app_host(FakePage("https://books5.margbooks.com/dashboard")) is None
    assert settings.BASE_URL == "https://books5.margbooks.com"


def test_login_ka_domain_app_ka_domain_nahi_maana_jata():
    """Agar abhi bhi accounts.margbooks.com par hain to wo app nahi hai."""
    assert auth.sync_app_host(FakePage("https://accounts.margbooks.com/user-company")) is None
    assert settings.BASE_URL == "https://books5.margbooks.com"


@pytest.mark.parametrize("url", ["", "about:blank", "data:text/html,x", None])
def test_ajeeb_url_par_kuch_nahi_badalta(url):
    assert auth.sync_app_host(FakePage(url)) is None
    assert settings.BASE_URL == "https://books5.margbooks.com"


def test_login_har_raste_se_host_sync_karta_hai():
    """Naya login aur saved-session dono -- koi bhi raasta chhoot na jaye."""
    import inspect
    src = inspect.getsource(auth.login)
    assert src.count("sync_app_host(") >= 2, "login ke kisi raaste me host sync nahi hota"
