# Scenario pack: user and role management (J15 `user-role-management`)

Status: DRAFT for QA/BA review (2026-10-08). Plan: `specs/user-role-management.md`. Related: J02 `scenarios/auth.md` (RB-*), `specs/roles.md`.

Source keys
- KB-UR = care portal "How to create User and Assign Roles to User in Marg Books ?" (`careportal_enriched_v5.csv`, chunk `2af160b5`): Invite form fields Email Id, Mobile No, User Name, Role (Manager/Operator), Company, Info; message "User Invited Successfully"; the invited user receives a confirmation.
- KB-RC = care portal "How to Assign Powers of ... to the user" pages (chunks `98332ecd`, `48e12b19`, `f2a6ecea`): Settings > "User Access & Privileges" > Configure > "User List" > Roles > Edit > "Role Configurations" window, pick a menu on the left, tick "Full", click "Update", message "Role Saved Successfully", then the user logs in again to get the rights.
- CODE = Tech Debt Radar code index: `POST UserConfiguration/RoleSave` (`margerpapi/Controllers/UserConfigurationController.cs:177-207`, writes `dbo.UserPower`), called by `UserMasterComponent.deleteData` and `UserConfigComponent.saveConfiguration` (chunk `f9653f08`); `POST User/SaveUser` (`margerpapi/Controllers/UserController.cs:200-220`, chunk `f4600ed3`).
- JIRA = `jira_vectordb.csv`: "not able to create new roles in user master" (chunk `bb44460d`); "Required Role rights setting in user power of new menu's" (chunk `434e18a3`).
- LIVE = observed on the QA tenant 2026-10-08 with the `garments` login (super admin), company "Garments New 29-08".
- UNVERIFIED = not observed and not citable; no value invented.

Environment facts (LIVE): the User List shows 2 users (the super admin and one other user); the Roles tab shows predefined roles Admin, Operator, Manager plus one custom role made by someone else. Every account in `.env` is the same super-admin login, so no limited user can sign in.

| ID | Type | Scenario | Expected | Source |
|---|---|---|---|---|
| UR-01 | positive | Create a role with a name, description and one right (Dashboard > Net Sale, Full) | "Role Saved Successfully"; dialog closes; role listed with its description | KB-RC; CODE RoleSave; LIVE |
| UR-02 | positive | Reopen a new role | Name, description and the granted right are shown as saved | LIVE |
| UR-03 | positive | Tick "Full" for one screen (Master > Ledger Master) | Create, Edit, Delete and Export of that row are ticked too | LIVE |
| UR-04 | positive | Edit a role: change description, grant Ledger Master Full, "Update" | "Role Saved Successfully"; reopening shows the new description and rights | KB-RC; LIVE |
| UR-05 | positive | Delete a role made by the test | Question "Do you want to delete selected role ?"; Yes gives "Delete Successfully"; role leaves the list | LIVE |
| UR-06 | negative | Save a role with no name | Dialog stays open; the "Role *" field is flagged (red icon); nothing saved; no message text | LIVE |
| UR-07 | permission | Delete a predefined role (Admin, Operator, Manager) | Refused: "Sorry, Pre-Defined Roles Can't Be Deletable Or Editable, Clone The Role Instead" | LIVE |
| UR-08 | permission | Edit a predefined role | Same refusal as UR-07; "Clone" is offered instead | LIVE |
| UR-09 | negative (defect) | Click the Edit (or Delete) icon of a custom role that is not the grid's selected row | Expected: that role's Role Configurations opens. Actual: the predefined refusal of UR-07 appears; the icon acts on the previously selected row | LIVE |
| UR-10 | boundary | "Invite User" when the plan's user limit is reached | Alert "Allowed 2 users only"; the invite form does not open | LIVE |
| UR-11 | boundary | Create a second role with the same name | NEEDS DECISION: live the app saves it, so two roles share one name | LIVE |
| UR-12 | positive | Invite a user with a role and company | UNVERIFIED (not run): "User Invited Successfully" and a confirmation sent to the invitee; blocked by UR-10 and by the real message | KB-UR |
| UR-13 | positive | Edit a user's role, deactivate (Status "De-Active") and delete a user | UNVERIFIED (not run): only users made by tests may be changed and none can be made | LIVE (Status select Active/De-Active exists) |
| UR-14 | permission | A user with a limited role signs in and opens a page outside the role | UNVERIFIED: needs a limited login (see J02 RB-03, Q3) | KB-RC (re-login needed after a rights change) |
| UR-15 | tenancy | A role created in one company is offered in another company | UNVERIFIED | none |
| UR-16 | negative | Role name length limit and special characters | UNVERIFIED (no maxlength seen on `#txtrolenamep`) | LIVE |

## KB vs live app
- KB-RC opens the screen from Settings > "User Access & Privileges" > Configure; live the same screen is `/mstr/usermaster` (title "User List").
- KB-RC names the edit button "Update"; live the create dialog has "F10 Save" and the edit dialog "F10 Update" plus "Common Rights".
- JIRA reports roles could not be created; live, creating a role works.
- KB-UR lets the admin invite users freely; live the plan caps users ("Allowed 2 users only").
