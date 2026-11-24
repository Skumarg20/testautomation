"""Option fields of the Sale Bill Setting window that the round-2 C1 cases hold, with their source.

Ids and tabs: UtililityComponent/ControlRoom/salebill.setting.html - Basic tab ends at line 280, so
`freeQtyConditionOnSale` (:799), `dealFrom` (:846) and `lotRateCalculation` (:1609) are on the Advance tab.
Option texts are the lookup rows of margbookscoreapi/margerpdata/DatabaseJson/lookup.json: Free Deal From
"Master / Batch / Manual / Lot / Lot & Free" (type 1031), Lot Rate Calculation "F7 Key / Always / Not
Applicable" (type 1240), Net Scheme Formula 1..4 (type 1242).
"""

from pages.sale.manual.option_settings import SettingField

FREE_QTY_ON_SALE = SettingField("freeQtyConditionOnSale", "Free Quantity Required in Sale", True)
FREE_DEAL_FROM = SettingField("dealFrom", "Free Deal From", True)
LOT_RATE_CALCULATION = SettingField("lotRateCalculation", "Lot Rate Calculation", True)

FREE_DEAL_SOURCES = ("Master", "Batch", "Manual", "Lot", "Lot & Free")
LOT_RATE_OPTIONS = ("F7 Key", "Always", "Not Applicable")
