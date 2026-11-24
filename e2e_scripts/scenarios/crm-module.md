# Scenario pack: crm-module (J36, P3, layer e2e)

Status: DRAFT (analyst), updated after live exploration. KB citations as `file#chunk_id(first 8)`. Live findings are in `specs/crm-module.md`.

## What "CRM" is in MargBooks
MargBooks has no lead / enquiry / follow-up CRM. The top-level **CRM** menu groups customer-relationship screens:
- Home Delivery (`/homedelivery`): assign a sale bill to a salesperson, update status Pending / Delivered (`careportal_enriched_v5.csv#9f42e326`, `codekb:MargBooks:screen#0dcec651`, `onedrive_processed_data.csv#387ff2b3`).
- Prescription Reminder (`/crm/prescription/:type`, chemist trade): due reminders from saved prescriptions (`codekb:MargBooks:screen#3ccf611a`, `careportal_enriched_v5.csv#89cb8177`, schema `codekb:MargBooks:schema#cb8ac0d9`).
- Pending Approvals (`/pending-grid`, `crm.module.ts:24`): approve purchase orders sent for approval (`codekb:MargBooks:screen#70858be0`, `careportal_enriched_v5.csv#eead3cf6`).
- Loyalty Management (`/loyalty/list`, `/loyalty/create-loyalty`, `crm.module.ts:21-23`): needs Control Room "Loyalty Management = Yes" (tenant-wide) (`careportal_enriched_v5.csv#01f1d953`, `codekb:MargBooks:screen#b4a424cb`, `#1a71fbf9`).
- Sidebar evidence: chemist sidebar "CRM, expanded to Home Delievery, Prescription Remi... and Pending Approvals" (`onedrive_processed_data.csv#10e7ca31`); CRM listed in top menu (`careportal_enriched_v5.csv#d3e3adba`, `scenarios/auth.md` RB-01).

The brief's "leads / enquiries / follow-ups / activities / status pipeline" do not exist as a MargBooks module (searches for lead/enquiry/follow-up returned only the signup-lead API `codekb:MargBooks:api#a3e1fd51` and the partner BSS panel `onedrive_processed_data.csv#5708cb33`, which are not tenant screens). Customer master is under Master > Other Master > Customer and needs its own module switch (`careportal_enriched_v5.csv#8659e05b`); it is not CRM.

## Cases
| ID | Type | Case | Source |
|---|---|---|---|
| CRM-01 | positive | Super admin sees a CRM group in the sidebar with its entries | `onedrive_processed_data.csv#10e7ca31` |
| CRM-02 | positive | Each CRM entry opens its screen without the not-authorized page | KB routes above |
| HD-01 | positive | Home Delivery lists sale bills with a status column and Assign To | `careportal_enriched_v5.csv#9f42e326` |
| HD-02 | positive | Update Status on an own bill: Pending -> Delivered, saved with "Record saved successfully" | `careportal_enriched_v5.csv#9f42e326` (UNVERIFIED: needs a bill flagged for home delivery) |
| HD-04 | positive | The Delivered status filter can be chosen | LIVE |
| HD-03 | negative | Assign To with no bill ticked is refused | UNVERIFIED |
| PA-01 | positive | Pending Approvals opens with a status filter | `codekb:MargBooks:screen#70858be0` (form field `status`) |
| PA-03 | positive | The All status filter can be chosen and a count is shown | LIVE |
| PA-02 | positive | An own purchase order sent for approval is listed and can be approved | `careportal_enriched_v5.csv#eead3cf6` (needs an approval workflow = tenant-wide setup; NEEDS DECISION) |
| PR-01 | positive | Prescription Reminder report opens (chemist) | `codekb:MargBooks:screen#3ccf611a` |
| PR-02 | edge | Jira: "prescription reminder object reference error" | `jira_vectordb.csv#45d38f3b` |
| PR-03 | edge | Support: saved prescription not showing in reminder list | `support_tickets_vectordb.csv#e231f51d` |
| LY-01 | positive | Loyalty setup is saved the first time ("Record Saved Successfully.") | `careportal_enriched_v5.csv#01f1d953`; LIVE (probe) |
| LY-02 | positive | Changed points are updated ("Record Updated Successfully.") and shown on reopen | LIVE |
| LY-03 | negative | Update with Rs. emptied is refused: "Please Enter The Required Details!" | LIVE |
| LY-04 | negative | After a refused update the stored Rs. is unchanged | LIVE |
| LY-05 | edge | Esc Close asks "Are you sure you want to close?" | LIVE |
| LY-06 | edge | Delete the setup | not possible: no UI action, no API (`codekb:MargBooks:api#c84bab19`) |

## Safety
Reminders and approvals can e-mail / SMS real contacts (`careportal_enriched_v5.csv#eead3cf6`: "All approvers will receive an email notification"). Tests must not send reminders or trigger approval mails.
