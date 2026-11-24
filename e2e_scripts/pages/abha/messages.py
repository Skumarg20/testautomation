"""The ABHA screens' warning texts, as the Angular source writes them (file:line per text).

Matched as patterns because the notifier toast may change case and whitespace; typos in the source ("Invaild",
the double space in "Please  Enter") are part of the expected text.
"""

import re

# abha-patient-registration.component.ts
AADHAAR_REQUIRED = re.compile(r"Please Enter Valid Aadhaar Number")  # :205
MOBILE_REQUIRED = re.compile(r"Please Enter Valid Corresponding Mobile Number")  # :208
OTP_REQUIRED = re.compile(r"Please Enter Received OTP")  # :212, also download .ts:595
CAPTCHA_REQUIRED = re.compile(r"Please Enter CAPTCHA")  # :216, also download .ts:325,520
CAPTCHA_WRONG = re.compile(r"Invalid CAPTCHA")  # :223, also download .ts:328,523
AADHAAR_UNKNOWN = re.compile(r"Invaild Aadhaar No\.")  # :171 (sic)

# AbhaEnum, Globals/global.ts:21279-21280, raised by abha-patient-consent.component.ts:62-69
TERMS_NOT_TICKED = re.compile(r"Please read and tick all the terms and conditions")
CONSENT_NAME_REQUIRED = re.compile(r"Please enter your full name as per Aadhar card")

# abha-patient-card-download.ts
DOWNLOAD_MOBILE_REQUIRED = re.compile(r"Please\s+Enter Mobile No\.")  # :518, two spaces in the source
FULL_ABHA_NUMBER_REQUIRED = re.compile(r"Please Enter Full ABHA Number")  # :310
ABHA_ADDRESS_REQUIRED = re.compile(r"Please Enter ABHA Address")  # :347
DOWNLOAD_AADHAAR_REQUIRED = re.compile(r"Please Enter Aadhaar No\.")  # :554
ABHA_ADDRESS_NOT_REGISTERED = re.compile(r"Invalid ABHA Address Or ABHA Address Not Register")  # :379
AADHAAR_NOT_REGISTERED = re.compile(r"Invalid Aadhaar Number Or Aadhaar Number Not Register")  # :505

# abha-address.component.ts
ABHA_ADDRESS_NOT_VALID = re.compile(r"ABHA Address Not Valid")  # :109
ABHA_ADDRESS_TAKEN = re.compile(  # :89-91, AbhaEnum Globals/global.ts:21278
    r"This ABHA Address already exists\. Please create with unique ABHA address"
)
ABHA_ADDRESS_CREATED = re.compile(r"ABHA Address Successfully Created")  # :94
