"""What J21's screens must never send: the endpoints of the scenario pack's safety frame
(`scenarios/notifications-export.md`), the WhatsApp senders behind a report share (`Common.service.ts`
SendWhatsappMethod and the desktop bridge), and `Profiler/Save`, which the desktop-notification toggle writes
for the shared user. Guarded by `pages/components/send_guard.py`; a test that drives a send answers the
endpoint with its own stub (`pages/components/stubbed_endpoint.py`), which the guard never sees."""

import re

DELIVERY_OR_GLOBAL_WRITE = re.compile(
    r"(Template/SendEmailPdfExcel|SendBulkSMSTemplate|BulkReminderInsert|InsertBulkReminderData|"
    r"WorkFlow/SchedulerSave|Notification/InsertNotification|Notification/SendWhatsapp|/api/SendMessage|"
    r"Profiler/Save)",
    re.IGNORECASE,
)
EMAIL_SEND = re.compile(r"Template/SendEmailPdfExcel", re.IGNORECASE)
# A report share posts to the WhatsApp service's /api/SendMessage (seen live 2026-10-14).
WHATSAPP_SEND = re.compile(
    r"(Notification/SendWhatsapp|whatsapp\.margbooks\.com/api/SendMessage)", re.IGNORECASE
)
SMS_SEND = re.compile(r"RegisterUser/SendBulkSMSTemplate", re.IGNORECASE)
REMINDER_RECORD = re.compile(r"Reports/InsertBulkReminderData", re.IGNORECASE)
SCHEDULE_SAVE = re.compile(r"WorkFlow/SchedulerSave", re.IGNORECASE)
