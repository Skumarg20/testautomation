# Plan: J26 Unit / UQC / HSN rate masters (unit-uqc-hsn-rate-masters)

Scenario pack: `scenarios/unit-uqc-hsn-rate-masters.md`. Tests: `tests/journeys/unit_hsn/` (`test_unit_master.py`, `test_hsn_master.py`, `test_item_usage.py`). Page objects: `pages/unit_hsn/`. Data: `test_data/unit_hsn.py`.
Status: DRAFT for QA/BA review. Observed live 2026-10-09 (QA tenant, `garments` login, company "Garments New 29-08").

## Preconditions
- `page_as("garments")`, company pinned to Garments New 29-08, dashboard open.
- Each test creates its own unit / HSN code (and item) and the `records` fixture deletes them in teardown: items first, then units, then HSN codes (in-use masters cannot be deleted).
- Names: the unit field holds 10 characters, so units are `QA` + 7 run-id characters + a serial digit; HSN codes are 8 digits `9` + 6 digits from the run id + a serial; HSN names are `QA-<run_id>-HSN<n>`.
- Navigation: Unit via the sidebar Master > Inventory Master > Unit. HSN list by its route `/mstr/hsn`: the sidebar link could not be matched by the shared link-name regex ("/" in "HSN / SAC" breaks Playwright's regex selector, and an escaped version found no link); its exact accessible name is still to be checked. The HSN list is switched to "Search By: HSN Code".

## Locators (verified live)
| Thing | Locator |
|---|---|
| Unit list | URL `/mstr/unit`; heading "Unit List"; button "Create/F2"; searchbox "Search" (exact); grid columns Unit Name, UQC (e.g. "BOX-BOX", "PCS-PIECES"), Action ("Edit/F3", "Delete") |
| Unit form | dialog heading "Create Unit"; `#txtUnitName` (maxlength 10); UQC combobox `#addUnit` placeholder "Search here.." (maxlength 3); `#btn-Save`, `#btn-Clear`, `#btn-Close` |
| HSN list | URL `/mstr/hsn`; heading "HSN/SAC List"; "Create/F2"; searchbox "Search"; a select "Search By" (Name / HSN Code); grid Name, HSN Code, Action |
| HSN form | dialog heading "Create HSN/SAC"; `#inphsncode` (maxlength 8), `#inphsnname` (maxlength 25); no GST rate fields shown on this tenant |

## Observations (live, 2026-10-09)
| Case | Seen |
|---|---|
| Unit save | success toast "Data Saved Successfully !"; row shows name + UQC (e.g. "BOX-BOX") |
| UQC pick | `#addUnit` opens a listbox of "<code>-<desc>" options after one key; click the option. With Unit Name empty, any key in UQC moves focus back to Unit Name (typed text lands in the name) |
| Unit duplicate (same or other letter case) | warning-free toast "Unit Already Exists !"; form stays open |
| Unit empty name | no toast; inline "Unit name required !"; form stays open |
| Unit name 15 chars | saved, cut to 10 characters |
| Unit edit | heading "Modify Unit", `#btn-Update`; toast "Data Updated Successfully !" |
| Unit delete | confirm "Are you sure you want to delete?" (`#btnYes`); toast "Record Deleted Successfully." |
| Predefined unit delete (TUBE) | warning "Pre-Defined Unit Can't Be Deleted!" with no confirmation |
| HSN save | toast "Record Saved Successfully."; row Name + HSN Code |
| HSN duplicate code | ACCEPTED: a second row with the same code is saved (defect candidate) |
| HSN letters "ABCD12" | ACCEPTED (defect candidate; invalid HSN breaks e-way bill upload, KB `#514affd4`) |
| HSN code 10 digits | cut to 8 by maxlength |
| HSN empty code | "Record Saved Successfully."; the text typed into Name landed in the code field (focus forced back to the empty code), so a record with code "QA-prb6-" and no name was saved |
| HSN edit | heading "Modify HSN/SAC", `#btn-Update`; toast "Record Updated Successfully." |
| HSN delete | confirm "Are you sure you want to delete the selected Record?"; toast "Record Deleted Successfully." |
| Toast kinds | class `notifier__notification--success` / `--warning` / `--error` (unit duplicate = warning) |
| New unit + HSN in Create Item | both offered in the Unit 1st / HSN lookups; item saved; Item List unit column shows the unit, Tax Info "HSN/SAC" shows the code |
| Delete unit used by an item | confirmation asked first, then error toast "ItemAre Available For This Unit."; unit stays |
| Delete HSN used by an item | confirmation asked first, then error toast "Item Are Available For This Hsn."; code stays |

## Plans (one test each)
| Plan | Scenario | Expected (seen live unless noted) | Test |
|---|---|---|---|
| UH-1 | UN-01, UN-02 | DERIVED (the list has a UQC column, filled for predefined units): new unit listed with UQC "BOX-BOX". Live: the UQC cell is empty for user units, even after a full reload -> fails, defect D3 | `test_new_unit_is_listed_with_its_uqc` |
| UH-1b | UN-02 | Modify Unit of the new unit shows UQC "BOX-BOX" (the UQC is stored) | `test_saved_unit_keeps_its_uqc` |
| UH-2 | UN-04 | "Unit name required !", dialog stays | `test_unit_without_name_is_not_saved` |
| UH-3 | UN-05 | warning "Unit Already Exists !" | `test_duplicate_unit_name_is_refused` |
| UH-4 | UN-05 | same warning for the lower-case twin | `test_duplicate_unit_check_ignores_letter_case` |
| UH-5 | UN-03 | 13-character name saved as its first 10 | `test_unit_name_is_cut_to_ten_characters` |
| UH-6 | UN-06 | Rename, Update: "Data Updated Successfully !"; new name listed, old name gone | `test_renamed_unit_replaces_old_name_in_list` |
| UH-6b | UN-06 | UQC changed to "PCS-PIECES", Update; reopened form shows "PCS-PIECES" | `test_changed_uqc_is_kept` |
| UH-7 | UN-09 | warning "Pre-Defined Unit Can't Be Deleted!" for TUBE, no confirmation | `test_predefined_unit_cannot_be_deleted` |
| UH-8 | UN-07 | "Record Deleted Successfully."; not listed | `test_unused_unit_is_deleted` |
| UH-9 | HS-01, HS-02 | Code listed with its name | `test_new_hsn_code_is_listed_with_its_name` |
| UH-10 | HS-03 | 10 digits typed, first 8 saved | `test_hsn_code_is_cut_to_eight_digits` |
| UH-11 | HS-05 | DERIVED (KB: HSN is numeric): a code with letters is not listed after Save. Live: saved -> fails, defect D1 | `test_hsn_code_with_letters_is_refused` |
| UH-12 | HS-04 | DERIVED (code is marked mandatory "*"): nothing saved (the name text is not listed as a code). Probe: saved with the name text as code (defect D2); not reproduced in the second suite run, see NEEDS DECISION 4 | `test_hsn_without_code_is_not_saved` |
| UH-13 | HS-07 | "Record Updated Successfully."; new name listed | `test_renamed_hsn_code_is_listed_with_new_name` |
| UH-14 | HS-08 | "Record Deleted Successfully."; not listed | `test_unused_hsn_code_is_deleted` |
| UH-U1 | UN-10, HS-10 | Item saved with the new unit and code; list and Tax Info show them | `test_item_is_saved_with_new_unit_and_hsn_code` |
| UH-U2 | UN-08 | "ItemAre Available For This Unit."; unit still listed | `test_unit_used_by_an_item_cannot_be_deleted` |
| UH-U3 | HS-09 | "Item Are Available For This Hsn."; code still listed | `test_hsn_code_used_by_an_item_cannot_be_deleted` |

## NEEDS DECISION
1. HSN code input allows 8 characters (`maxlength=8`) while the DB column is 10 and the KB says codes can be 2/4/6/8 digits.
2. No GST rate fields on the HSN form here (CODE has cgst/sgst/igst/cess): the "HSN rate" part of J26 is not covered. Which setting shows them, and may the suite turn it on (tenant-wide, would need `xdist_group`)? HSN-wise rate change (Ease of GST, HS-12) is tenant-wide and left out.
3. D1: HSN code "ABCD12" is accepted. Should the code be digits only (and 2/4/6/8 long)? UH-11 asserts refusal.
4. D2 (seen in the probe only): after clearing the code field and filling the name, focus is forced back to the code field, so text typed for the name goes into the code, and the record is saved ("Record Saved Successfully."). UH-12 asserts nothing is saved.
5. Duplicate HSN codes are accepted (same code saved three times in the probe). Not asserted: no source says codes must be unique (several names per code may be intended). Decide the rule.
6. Unit delete asks "Are you sure you want to delete?" before checking for items, then refuses; same for HSN. Should it refuse before asking (as for predefined units)?
8. D3: the Unit List UQC column is empty for user-created units (predefined units show e.g. "BOX-BOX"), although Modify Unit shows the saved UQC. UH-1 asserts the list shows it.
7. Unit name and HSN code are silently cut to 10 / 8 characters (UH-5, UH-10 pin this). Confirm, and confirm that unit names cannot follow the `QA-<run_id>-` naming rule.
