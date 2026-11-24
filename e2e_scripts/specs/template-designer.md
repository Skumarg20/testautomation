# Spec: template-designer (J32) - DRAFT for QA/BA review

Scenario pack: `scenarios/template-designer.md`. Observed live on premargbooks (account `garments`, company
"Garments New 29-08") on 2026-10-09 and 2026-10-10.

## Screen as observed
- Utilities & Tools > Template Management > **Invoice Template** opens `/print-template`,
  "Template Customize - <voucher type>". The voucher types are listed on the left; Sale Bill is one of them.
- "Predefined Template" shows one card. "Show More" lists all of them: Invoice-STD Light, Thermal, Thermal
  3-Inch, Full-Page, Pharma Full Page, Chemist Billing, General Billing, Landscape Full Page, Bill To Ship To,
  Parameter-Page, Invoice-STD Dark/Vivid/Grey and Para-Serial-Page. Each card has Customise and Set as Default.
- "Custom Template" cards have Delete and Export buttons, which only show on hover, plus Customise. The
  default card shows a check mark (✔) and no Set as Default button.
- Customise opens the **Template Studio** dialog. Its tabs are General (Title Text, colours, font size,
  orientation, margins, paper size, names of the print copies), Company, Party, Item Table and Footer. The
  field rows are a checkbox, a width and a label; the checkbox ids are `<field>-control`, e.g. `free-control`.
  Under the form is a live preview of a sample bill. At the bottom: a "Save as Template" checkbox, the name
  box and Save.
- Saving shows the toast "Template Saved Successfully". An empty name gets the toast "Template Name
  Required" and the dialog stays open.
- Delete asks for confirmation ("Are you sure you want to delete the selected Record?", Yes/No).
- The Invoice Design screen (FastReport designer, needs a password) was not explored.

## Tests (tests/journeys/print_templates/)
| Test | Scenario |
|---|---|
| test_copy_of_built_in_template_is_listed_as_custom | TD-02 |
| test_added_item_column_shows_in_the_preview | TD-03/TD-04 (studio preview) |
| test_added_item_column_is_kept_after_saving | TD-03 |
| test_edited_title_is_kept_after_saving | TD-03, fails, see defect D1 |
| test_renamed_template_is_listed_under_the_new_name_only | TD-03 |
| test_deleted_template_leaves_the_list | TD-05 |
| test_declined_deletion_keeps_the_template | TD-08 |
| test_template_without_a_name_is_refused | TD-06 |
| test_second_template_with_the_same_name_is_not_saved | TD-07 |

## Defects / observations
- D1: the edited Title Text is not kept. Steps: Sale Bill > Customise Full-Page > set Title Text to X >
  Save as Template, name N > Save ("Template Saved Successfully") > Customise N. Expected: Title Text X.
  Actual: "SALE BILL". Seen in 4 runs on 2026-10-09 and 2026-10-10. The studio preview never shows the title
  either: its heading cell reads "Sale Bill" while the box reads "SALE BILL". The Item Table column change is
  kept, so saving works in general.
- O1: changing an Item Table label (Product -> other text) does not change the preview column header.
  Seen once; no test written.
- O2: in a probe on 2026-10-09 a second "Save as Template" under an existing name created a second card with
  the same name. In the 2026-10-10 runs the duplicate test passed (still one card). Watch this test.

## NEEDS DECISION
1. **Saving a custom template makes it the Sale Bill default of the company** (✔ on the card,
   `isdefault=1` in `PrintTemplate/PrintTemplateList`). Before the tests there was no Sale Bill custom
   default. After the custom template is deleted, the list looks as it did before. So for the length of a test,
   other suites that print Sale Bills use a QA copy of Full-Page. The tests are in
   `xdist_group("garments-print-templates")` and always delete their templates. Is that acceptable, and is
   "becomes default" intended?
2. Print preview of a real sale bill with the custom template is not automated. The Garments sale bill list
   showed no rows in its default period, and creating a garments bill is broken
   (`GarmentsSalePage.open_new_bill`). The studio's live preview of a sample bill is used instead. Need a QA
   decision: preview an existing bill read-only, or create one via `pages/barcode/barcode_sale_bill.py`.
3. Set as Default is not exercised. It changes tenant state and the original default could not be read
   reliably (predefined defaults are not flagged in the list API).
4. The Invoice Design (FastReport) screen asks for a password. It is out of scope unless a QA secret is given.
