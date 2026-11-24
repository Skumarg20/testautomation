"""The login form submitted with the keyboard while offline (J35 DS-26).

The offline overlay covers the login screen too (`app.component.ts:29-35`), so the pointer cannot press the
sign-in button; Enter in the password field still submits. Ids as `pages/login_page.py` (single-step login,
UAT/preprod). DRAFT: not seen live.
"""

from pages.login_page import LoginPage


class OfflineLogin(LoginPage):
    def submit_with_keyboard(self, user: str, password: str) -> None:
        self.user_id.fill(user)
        self.password.fill(password)
        self.password.press("Enter")
