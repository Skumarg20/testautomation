# Scenario pack: Unit / UQC / HSN rate masters (J26, journey id `unit-uqc-hsn-rate-masters`)

Status: DRAFT for QA/BA review (2026-10-09). Journey J26, priority P2, layer e2e. Planner output: `specs/unit-uqc-hsn-rate-masters.md`.

Scope: Master > Inventory Master > Unit (unit name + UQC for GST e-returns) and Master > Inventory Master > HSN / SAC (code + name, GST rate fields where enabled), and their use in the item master (Unit 1st, HSN/SAC lookups). Item master CRUD itself is `item-master-crud`; tax-rate changes through Utilities > Ease of GST are tenant-wide and out of scope here.

Source keys
- KB = Tech Debt Radar KB chunk, cited `file#chunk_id(first 8)`.
- CODE = Tech Debt Radar code/schema index, cited the same way.
- UNVERIFIED = not citable; stated as a question, no value invented.

## Unit master

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| UN-01 | positive | Open Master > Inventory Master > Unit | "Unit List" with a predefined list, Create button | KB `careportal_enriched_v5.csv#78d0fc17` |
| UN-02 | positive | Create a unit: Unit Name, UQC, Save | Unit saved and listed with its UQC | KB `#78d0fc17`; CODE `codekb:MargBooks:screen#7aeffc75` (form fields unitname, uqc, alias, printname) |
| UN-03 | boundary | Unit name length | DB column is `nvarchar(10)` (alias 10, print name 20); longer input must be cut or refused | CODE `codekb:MargBooks:schema#8cc5ba8f`, `#75d95203` |
| UN-04 | negative | Save without a unit name | Refused (name is mandatory). Wording UNVERIFIED | CODE `#7aeffc75`; UNVERIFIED |
| UN-05 | negative | Duplicate unit name in the company | Refused. Wording and case rule UNVERIFIED | UNVERIFIED |
| UN-06 | positive | Modify a unit (Edit icon, change, Update) | Change shown in the list | KB `#78d0fc17`; CODE `PUT Unit/Update` -> `usp_UnitMasterUpdate` (`schema#8cc5ba8f`) |
| UN-07 | positive | Delete an unused user unit, confirm Yes | Removed from the list | KB `careportal_enriched_v5.csv#ccfaf1aa` |
| UN-08 | negative | Delete a unit selected in an item | Refused: "neither predefined ... nor if any unit is already selected in the item" can be deleted | KB `#ccfaf1aa` |
| UN-09 | negative | Delete a predefined unit | Refused | KB `#ccfaf1aa` |
| UN-10 | usage | New unit offered in item master Unit 1st lookup | The unit is selectable when creating an item | KB `careportal_enriched_v5.csv#7e11d1c2`, `#86336d40` |
| UN-11 | known issue | GSTR-1 HSN summary shows the wrong UQC (PCS) when billed in strip/box | Regression risk on UQC mapping; not reproduced here | KB `support_tickets_vectordb.csv#7c1aa83c` |

## HSN / SAC master

| ID | Type | Scenario | Expected result | Source |
|---|---|---|---|---|
| HS-01 | positive | Open Master > Inventory Master > HSN / SAC | "HSN/SAC List" with Create, search | KB `careportal_enriched_v5.csv#320937c5`, `#27613ae1` |
| HS-02 | positive | Create: HSN/SAC Code + HSN/SAC Name, Save | Code created and listed | KB `#320937c5` |
| HS-03 | boundary | Code length | Codes "can be of any digit such as 2,4,6,8"; DB `hsn varchar(10)`, `hsnname varchar(25)` | KB `#27613ae1`; CODE `schema#c660f768`, `#63df901e` |
| HS-04 | negative | Save without a code | Refused. Wording UNVERIFIED | UNVERIFIED |
| HS-05 | negative | Non-numeric / invalid code | UNVERIFIED whether the UI refuses letters or odd lengths | UNVERIFIED; KB `#514affd4` (invalid HSN fails e-way bill upload) |
| HS-06 | negative | Duplicate code | UNVERIFIED | UNVERIFIED |
| HS-07 | positive | Modify a code (Edit, change, Update) | Updated | KB `careportal_enriched_v5.csv#1952d682`; CODE `api#f99b4842` |
| HS-08 | positive | Delete an unused code with Yes on "Are you sure you want to delete the selected Record?" | Removed (soft delete, `isdelete = 1`) | KB `#1952d682`; CODE `schema#61e4990a` |
| HS-09 | negative | Delete a code set on an item | "cannot be deleted" | KB `#1952d682` |
| HS-10 | usage | New code offered in the item master HSN/SAC lookup | Selectable | KB `#7e11d1c2` |
| HS-11 | rate | HSN GST rate fields (cgst, sgst, igst, cess) on the HSN form | The Angular form has them; whether they are shown depends on settings. UNVERIFIED live | CODE `codekb:MargBooks:screen#bca52e2d` |
| HS-12 | rate | Changing GST rate HSN-wise (Utilities > Ease of GST) | Tenant-wide change, needs "Sure"; out of scope | KB `#652cd5f2` |
| HS-13 | config | Control Room renames the "HSN / SAC" field | Field label may differ per tenant | KB `#d56d2fcd` |
