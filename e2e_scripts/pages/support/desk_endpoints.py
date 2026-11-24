"""The API calls of the support screens (`src/app/Globals/global.ts:121`, `:252-256` in the Angular source).

Writes go on to Marg's live support desk, and a saved ticket also queues a real WhatsApp and email
(`margerpapi/Controllers/MargSupportController.cs:229-288`), so `SUPPORT_WRITES` is what the `SendGuard`
aborts in every J41 test. It also lists the OTP and message dispatch calls of the app, so a stray one
cannot leave the browser either (`global.ts:365`, `:460`, `:472-473`, `:534-538`, `:18289`, `:18295-18296`).
"""

import re

SUPPORT_WRITES = re.compile(
    r"(MargSupport/Save|MBSupportDeleteRecord|MBSupportUpdateStatus|MBSupportInsertChatRecord|"
    r"RegisterUser/CheckOTP|PharmaNxt/SendOTP|RegisterUser/SendSMSInQue|RegisterUser/SendSMSTemplate|"
    r"RegisterUser/SendBulkSMSTemplate|RegisterUser/ForgotPasswordMail|Template/SendEmailPdfExcel|"
    r"Notification/SendWhatsapp|Whatsapp/sendMessage)",
    re.IGNORECASE,
)

SAVE_TICKET = re.compile(r"MargSupport/Save(\?|$)", re.IGNORECASE)
DELETE_TICKET = re.compile(r"MargSupport/MBSupportDeleteRecord", re.IGNORECASE)
REOPEN_MESSAGE = re.compile(r"MargSupport/MBSupportUpdateStatus", re.IGNORECASE)

TICKET_LIST = re.compile(r"MargSupport/MargPrtnerSupprtDetail", re.IGNORECASE)
DISPOSITIONS = re.compile(r"MargSupport/MargSupportStaticData", re.IGNORECASE)
CHAT_HISTORY = re.compile(r"MargSupport/MBSupportGetChatRecord", re.IGNORECASE)
SUGGESTIONS = re.compile(r"QuestionSearchMargBook/GetQuestionSugestion", re.IGNORECASE)
