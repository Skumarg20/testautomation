"""Sale-bill header presets. Parties are ledgers that must exist in the QA tenant."""

from test_data.models import BillHeader, HeaderTag

CASH_ACCOUNT = "Cash Account"
CASH_PATIENT = "CASH Patient"
CASH_DOCTOR = "Cash Doctor"

_CASH_BILL = BillHeader(party_name=CASH_ACCOUNT, patient_name=CASH_PATIENT, doctor=CASH_DOCTOR)

HEADERS: dict[HeaderTag, BillHeader] = {
    HeaderTag.BASE: _CASH_BILL,
    HeaderTag.AGENCY_DISCOUNT: BillHeader(party_name="Bs"),
    HeaderTag.SPECIAL_DISCOUNT: BillHeader(party_name="Special Discount"),
    HeaderTag.MASTER_DISCOUNT: BillHeader(party_name="Ledger Master Discount"),
    HeaderTag.PARTY_WISE_AGENCY_DISCOUNT: BillHeader(party_name="Party Wise Agency Discount"),
    HeaderTag.BACK_DATE_ALLOWED: BillHeader(
        party_name=CASH_ACCOUNT, patient_name=CASH_PATIENT, doctor=CASH_DOCTOR, date_offset_days=-1
    ),
    HeaderTag.FUTURE_DATE_ALLOWED: BillHeader(
        party_name=CASH_ACCOUNT, patient_name=CASH_PATIENT, doctor=CASH_DOCTOR, date_offset_days=1
    ),
    HeaderTag.FUTURE_DATE_NOT_ALLOWED: BillHeader(date_offset_days=1),
    HeaderTag.BACK_DATE_NOT_ALLOWED: BillHeader(date_offset_days=-1),
    HeaderTag.NO_PATIENT_OR_DOCTOR: BillHeader(party_name=CASH_ACCOUNT),
    HeaderTag.STORE: BillHeader(
        party_name=CASH_ACCOUNT, patient_name=CASH_PATIENT, doctor=CASH_DOCTOR, store="Test"
    ),
    HeaderTag.CONVERSION: BillHeader(
        party_name=CASH_ACCOUNT, patient_name=CASH_PATIENT, doctor=CASH_DOCTOR, sale_type="yes"
    ),
    HeaderTag.ALL_FIELDS: BillHeader(
        party_name=CASH_ACCOUNT,
        patient_name=CASH_PATIENT,
        doctor=CASH_DOCTOR,
        mr="Aman",
        store="delhi",
        address="delhi",
        sale_type="yes",
    ),
    HeaderTag.BILL_BY_BILL_SALE: BillHeader(
        party_name="Bill By Bill Sale", patient_name=CASH_PATIENT, doctor=CASH_DOCTOR
    ),
    HeaderTag.ON_ACCOUNT_SALE: BillHeader(
        party_name="On Account Sale", patient_name=CASH_PATIENT, doctor=CASH_DOCTOR
    ),
}
