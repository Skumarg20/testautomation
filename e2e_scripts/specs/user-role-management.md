# Plan: J15 user and role management (`user-role-management`)

Status: DRAFT for QA/BA review. Scenario pack: `scenarios/user-role-management.md`. Tests: `tests/journeys/admin/test_role_management.py`, `tests/journeys/admin/test_user_management.py`.
Explored live 2026-10-08 with throwaway probes (login `garments`, super admin, company "Garments New 29-08"). Every probe role was deleted; after the runs the Roles tab lists only Admin, Operator, Manager and the pre-existing custom role, and All Users lists 2 users.

## Preconditions
- `page_as("garments")`, dashboard open. Every configured account is the same super-admin login, so no limited user exists.
- Each test that needs a role makes `QA-<run_id>-Role` (`test_data/user_roles.new_role`). The `role` fixture deletes every row with that name afterwards (it loops because the app accepts duplicate names, UR-11).
- Predefined roles (Admin, Operator, Manager), existing users and the other custom role are never saved, edited or deleted. Clicking Delete on a predefined role only shows a refusal toast; no question is answered.

## Locators (verified live)
| Thing | Locator |
|---|---|
| Page | `/mstr/usermaster`, heading "User List"; button "Invite User"; tabs "All Users" / "Roles" |
| Roles tab | button "Create"; columns S.No., Role, Description, Action; row icons buttons "Edit/F3", "Delete" and the text "Clone" |
| Grid rows | ag-Grid pads itself with empty rows, so listed rows are those with a numeric S.No. cell |
| Role Configurations dialog | `dialog` with heading "Role Configurations"; name `#txtrolenamep`, description `#txtdescription` (labels not tied to inputs); menu links on the left (Dashboard, Master, ...); rights grid rows named by the screen, first checkbox = "Full", then Create/Edit/Delete/Export where the menu has them; buttons "F10 Save" (create), "F10 Update" and "Common Rights" (edit), "Esc Close" |
| Delete question | dialog text "Do you want to delete selected role ?"; both buttons are named "Close" (aria-label), told apart by their text Yes / No |
| Messages | toasts "Role Saved Successfully", "Delete Successfully", "Sorry, Pre-Defined Roles Can't Be Deletable Or Editable, Clone The Role Instead" (DOM text case differs from screen; matched case-blind) |
| Invite at limit | dialog "Alert!" with "Allowed 2 users only", button OK |
| Network | create/edit/delete all `POST /v4.2/UserConfiguration/RoleSave`; list `GET /v4.2/UserConfiguration/GetuserRole`; users `GET /v4.2/User/List` |

## Plans
| ID | Test | Steps | Expected |
|---|---|---|---|
| UR-01 | `test_new_role_is_listed_with_its_description` | Create with name, description, Dashboard > Net Sale Full; Save | toast "Role Saved Successfully", dialog closes, one row with the description |
| UR-02 | `test_right_granted_at_create_is_kept` | Select the row, Edit/F3 | name, description, Net Sale Full ticked |
| UR-03 | `test_full_right_ticks_every_right_of_that_screen` | Create dialog, Master > Ledger Master Full; close without saving | Full, Create, Edit, Delete, Export ticked |
| UR-04 | `test_edited_rights_and_description_are_kept` | Edit, new description, Ledger Master Full, F10 Update; reopen | "Role Saved Successfully"; new description and all Ledger Master rights ticked |
| UR-05 | `test_deleted_role_leaves_the_list` | Select, Delete, Yes | "Delete Successfully"; row gone |
| UR-06 | `test_role_without_a_name_is_not_saved` | Create, Save with empty name | dialog stays open, name input `ng-invalid` with a red icon, no message |
| UR-07 | `test_predefined_role_cannot_be_deleted` | Select Operator, Delete | refusal toast |
| UR-08 | `test_predefined_role_cannot_be_edited` | Select Operator, Edit/F3 | refusal toast |
| UR-09 | `test_edit_icon_opens_the_role_of_its_own_row` | Without selecting the row first, click Edit/F3 of the test's role | Expected: its Role Configurations opens. FAILS: app defect D-UR-1 |
| UR-10 | `test_invite_beyond_the_user_limit_names_the_limit` | All Users, count listed users, Invite User | alert "Allowed N users only" with N = users listed (2 live); no invite form, no message sent |

## App defect
D-UR-1 Row action icons act on the previously selected row. Steps: Roles tab, create role X, reload, click the Edit/F3 (or Delete) icon in X's row without first clicking the row. Expected: X opens for editing (or the delete question for X). Actual: toast "Sorry, Pre-Defined Roles Can't Be Deletable Or Editable, Clone The Role Instead"; selecting the row first and clicking again works.

## NEEDS DECISION
- UR-D1 Creating a user: "Invite User" is blocked by the plan ("Allowed 2 users only"), and KB-UR says an invite sends a real confirmation to the invitee. User create/edit/deactivate/delete (UR-12, UR-13) are not automated. Needs a test seat plus a mailbox/number the team owns, or an API to remove invited users.
- UR-D2 Limited-user denial (UR-14, J02 RB-03): needs a limited login in `.env` (`QA_OPERATOR_USER/PASS`) and the expected denial behaviour.
- UR-11 Duplicate role names: live a second role with the same name is saved. Is this allowed? If not, it is a defect.
- UR-15 Are roles per company or per login? Not checked.
- UR-16 Role name length / characters: no maxlength seen; limit unknown.
- The existing user's Status select (Active / De-Active) changes that user immediately; never automated against existing users.
