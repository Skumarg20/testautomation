"""Messages of the email setup screens, as seen live (specs/email-sms-whatsapp-setup.md)."""

import re

NAME_REQUIRED = "Name required !"
# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
INVALID_EMAIL = re.compile(r"Please Enter A Valid Email Id!", re.IGNORECASE)
