"""Sale Bill Setting fields the round-2 tests hold, with the choices each offers.

Ids are those of `salebill.setting.html` (UtililityComponent/ControlRoom). The visible texts of the choices
come from the API's static lookups (`margbookscoreapi/MargApp.MargErpDataTemplate/JsonData/lookup.json`;
lookup type in the comment on each field); they are matched case-blind, so a tenant that words one a little
differently fails with the list it offers.
"""

from pages.sale.manual.option_settings import SettingField

# lookup 1161: 0 Batchwise, 1 ItemWise (processout RatePick: "1" takes the item master, else the batch)
RATES_FROM = SettingField("rateFromMasterBatchDate", "Rates from master/batch", True)
BATCHWISE = "Batchwise"
ITEM_WISE = "ItemWise"
# lookup 1085: Cost, Extra+Cost, M.R.P., Purchase Rate, A-Rate ... E-Rate
DEFAULT_BILLING_RATE = SettingField("DefaultBillingRate", "Default Billing Rate", True)
A_RATE = "A-Rate"
# lookup 1122: Expiry, MFG Date, FIFO Date, Batch Name
BATCH_WINDOW_INDEX = SettingField("openBatchWindowIndexOn", "Batch window index on", True)
# select with the options false / true labelled No / Yes (salebill.setting.html:803-804)
FREE_QUANTITY = SettingField("freeQtyConditionOnSale", "Free Quantity Required in Sale", True)
# lookup 1093: Always, If In Master, As Per Master
FREE_QUANTITY_DECIMAL = SettingField(
    "freeQuantityRequiredinDecimal", "Free Quantity Required in Decimal", True
)
# lookup 1088: No, Price List, Ask, Ask w/o Price List
UPDATE_CHANGED_RATE = SettingField("updateChangedRate", "Update Changed Rate", True)
# lookup 1089: No, Product Special, Ask, Ask w/o Agency Discount
UPDATE_CHANGED_DISCOUNT = SettingField("updateChangedDiscount", "Update Changed Discount", True)
# lookup 1154: Ask always, Ask on * Key, No
ASK_NET_RATE = SettingField("askNetRate", "Ask Net Rate", True)
# lookup 1117: OnLeftArrowKey, Yes, No
ASK_BILL_NO = SettingField("askBillNo", "Ask Bill No.", True)
# lookup 1084: Rate * Quantity, Rate * Quantity - Discount, Net Amount
AMOUNT_CALCULATION = SettingField("amountCalculationOnBilling", "Amount Calculation On Billing", True)
# lookup 1119 shown by value: Master, Direct, Loop
PICK_MR_FROM = SettingField("mrFrom", "Pick MR From", True)
MR_REQUIRED = SettingField("txtisMR", "MR required?", True)
# lookup 1160: Percentage, Amount, Both(% and amount)
SHOW_BILL_MARGIN = SettingField("ShowBillwiseMargin", "Show Bill wise Margin in", True)
# yes / no list (YesNoData): the Ask Order No. and Order Date switch
ASK_ORDER_NO = SettingField("askOrderNoOrderDeliveryDate", "Ask Order No., Order Date", True)
# basic tab, top: Inclusive / Exclusive / Tax on MRP (CalculationType list)
GST_CALCULATION = SettingField("calculationTypeForSale", "GST calculation type")
