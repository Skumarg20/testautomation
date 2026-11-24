# Scenario pack: template-designer (J32, P2, e2e)

Template designer / print templates. Written by the test-analyst role from the KB (Tech Debt Radar).
Citations are `file#chunk_id(first 8)`. Anything not citable is marked UNVERIFIED.

## What the KB says the feature is

Two related screens live under **Utilities & Tools**:

1. **Invoice Template** ("Template Customize" window): pick the nature of the transaction (Sale Bill, ...),
   pick a predefined format (Full-Page, Parameter-Page, Pharma Full Page, Chemist Billing, General Billing...),
   **Set as Default** (message "Template Saved as Default Successfully"), click a template to view it full screen,
   **Customize / Edit** opens a "Print Setting(s)" window with tabs (General: Title Text, Name of Print Copy;
   Company: GSTIN, Status; Footer: Remark) and a Save button.
   careportal_enriched_v5.csv#9248cddc, #db9b405d, #b91e9dc1, #a0010e5d, #99951188, #51711603
2. **Invoice Design** ("Manage Template" window, FastReport designer): opens after an **Alert asking for a
   password**; choose Report Type (Sale Bill) and Report (format name); Data -> Data Sources -> drag a field
   (Party Name, GSTIN, Logo, Store Name...) onto the page; Properties -> Watermark; Export/Import; Delete
   with a Yes confirmation. careportal_enriched_v5.csv#c9245910, #f109d22e, #0ed26b21, #ac79c50f, #93a1f6a6,
   #79b59787, #49c1beef, #f2038896

Code index:
- `TemplateListingComponent` route `/create-template` (templates.module.ts) calls `POST PrintTemplate/SaveUpdateprint`
  and `GET PrintTemplate/DeleteTemplate`. codekb:MargBooks:screen#a9fb25d6
- `TemplateDesignComponent` routes `/` and `/downloadtemplate` of the templates module, has a gallery
  (`galleryTrade`) and premium templates. codekb:MargBooks:screen#6b64c60b
- `GET PrintTemplate/CheckDuplicate(linkid, reportype, name)`: template names are unique per report type.
  codekb:MargBooks:api#70a554e4, codekb:MargBooks:code#2aaa8373
- `POST PrintTemplate/SetDefaultTemplate`. codekb:MargBooks:api#666577e3
- Table `dbo.Customreports` has `templatename`, `isdefault`, `ispredefine`, `isDelete` (soft delete).
  codekb:MargBooks:schema#44cb1a3f

Jira / tickets (untrusted, paraphrased):
- "Change the displayed information in the invoice template preview" jira_vectordb.csv#eeb18dfd
- "serial parameter must not be visible (item tab) - invoice template designer" jira_vectordb.csv#556f04d9
- "Template save button disable functionality" jira_vectordb.csv#17598ae8
- "Remove the template name and add a Set as Default button" jira_vectordb.csv#93582712
- Field changed in template (heading text) not reflected in print: support_tickets_vectordb.csv#c65560e1 area,
  #39f871a4; party name missing from a custom template: jira_vectordb.csv#c789c265

## Scenarios

### Positive
- TD-01 Open the template screen from Utilities & Tools; the Sale Bill template list shows the predefined
  formats and marks the current default. (#9248cddc, #51711603)
- TD-02 Create a custom template as a copy of a built-in one, named `QA-<run_id>-...`; it appears in the list.
  (#a9fb25d6 SaveUpdateprint) UNVERIFIED which UI action copies.
- TD-03 Edit the custom template: change a field (e.g. title text) and rename it; the list shows the new name.
  (#9248cddc General tab Title Text) UNVERIFIED for custom templates.
- TD-04 Print preview of an existing sale bill using the custom template shows the edited field. Print preview
  only; never send to a printer. (#eeb18dfd preview) UNVERIFIED.
- TD-05 Delete the custom template with Yes in the confirmation; it is gone from the list. (#f2038896)

### Negative / validation
- TD-06 Saving a template with an empty name is refused. UNVERIFIED (name required implied by CheckDuplicate).
- TD-07 Saving a template with a name that already exists for the same report type is refused.
  (#70a554e4 CheckDuplicate)
- TD-08 Answering No to the delete confirmation keeps the template. (#f2038896)
- TD-09 Invoice Design asks for a password before opening Manage Template; a wrong password is refused.
  (#c9245910 etc.) UNVERIFIED message. Not automated if it needs a separate secret.

### Edge
- TD-10 Set as Default is tenant-wide state: only exercised if the original default is restored and verified
  in teardown (brief safety rule). (#51711603, #666577e3)
- TD-11 Name at max length / special characters. UNVERIFIED limits.
