"""Whether the selected company shows the ABHA screens, read the way the app itself decides it.

The app shows ABHA only for a chemist company (`SelectedCompany.bustype == 5`, `Globals/global.ts:18854`)
whose Control Room field 4426 "Abha Id for pharmacy store" is not blank (`processout.transaction.component.ts:
19926-19933`, `Common/common.function.ts:726-731`). Both values are in the app's local storage after login.

Only a yes/no for field 4426 leaves the browser: its value is the pharmacy's facility id and is never read
into the test.
"""

from dataclasses import dataclass

from pages.base_page import BasePage

CHEMIST_BUSINESS_TYPE = 5
ABHA_ID_FIELD = 4426

ABHA_SETUP_SCRIPT = """
() => {
    const stored = key => JSON.parse(
        localStorage.getItem(JSON.stringify({key: key, session: 'mb-session'})) || 'null');
    const company = stored('LoggedInUserInfo')?.SelectedCompany;
    const fields = stored('controlRoomData')?.profilerModel?.FieldsData || [];
    const abhaId = fields.find(f => f.fieldId === 4426)?.ActionData?.[6]?.action;
    return {businessType: Number(company?.bustype ?? -1), abhaIdSet: Boolean(abhaId)};
}
"""


@dataclass(frozen=True)
class AbhaSetup:
    business_type: int
    abha_id_set: bool

    @property
    def is_chemist(self) -> bool:
        return self.business_type == CHEMIST_BUSINESS_TYPE

    @property
    def shows_abha(self) -> bool:
        return self.is_chemist and self.abha_id_set


class AbhaSetupReader(BasePage):
    def read(self) -> AbhaSetup:
        """Call on a loaded app page (after the company is pinned)."""
        stored = self.page.evaluate(ABHA_SETUP_SCRIPT)
        return AbhaSetup(business_type=int(stored["businessType"]), abha_id_set=bool(stored["abhaIdSet"]))
