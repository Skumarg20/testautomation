"""The app's own "Internet Required for this option!" guards, reached behind the offline overlay (J35
DS-09..DS-12).

On preprod the root overlay covers every route while offline (`app.component.ts:29-35`), so the pointer
cannot reach the guarded links and buttons (pack KB vs live 3). The pack allows a test-only DOM tweak for
these rows: `lift_overlay` hides the overlay element after it has been shown, so the click lands on the
control and the app's own guard decides what happens. The browser stays offline throughout; the overlay is
only made transparent to the pointer, the app's state is untouched. DRAFT: written from the Angular source,
not seen live.
"""

import re

from playwright.sync_api import Page, expect

# Global.ts:19031 `AlertMsg.NoInternent`.
INTERNET_REQUIRED = "Internet Required for this option!"
WARNING_TIMEOUT_MS = 15_000
# Why CSS: the overlay is a bare div with no role or name; `locked-screen` is its only class of its own
# (app.component.ts:29).
OVERLAY = "margerpapp-root > div.locked-screen"
HIDE_OVERLAY_SCRIPT = f"""
() => document.querySelectorAll({OVERLAY!r}).forEach(el => {{ el.style.display = 'none'; }})
"""
# Third parties and real sends the guarded controls lead to when online; any request to them is aborted.
# Help portal (homelayout.component.ts:2686), WhatsApp host (environment.preprod.ts:72), list sends
# (global.ts:794 `UploadBills`, :518, `Template/SendEmailPdfExcel`), GST lookup (environment.preprod.ts:52,
# global.ts:18242-18244; a paid wallet call).
OUTSIDE_CALLS = re.compile(
    r"(care\.margcompusoft\.com|whatsapp\.margbooks\.com|BillSales/SalesInvoiceUpload|"
    r"Reports/InvoiceExportOfflineWhatsapp|Template/SendEmailPdfExcel|Notification/SendWhatsapp|"
    r"Whatsapp/sendMessage|gstcafenew\.margerp\.com|EInvoiceEncDec/EncryptAES|EInvoiceEncDec/DecryptAESGST)",
    re.IGNORECASE,
)


def lift_overlay(page: Page) -> None:
    """Test-only: hides the shown offline overlay so the pointer reaches the control under it."""
    page.evaluate(HIDE_OVERLAY_SCRIPT)


def expect_internet_required(page: Page) -> None:
    expect(page.get_by_text(INTERNET_REQUIRED).first).to_be_visible(timeout=WARNING_TIMEOUT_MS)
