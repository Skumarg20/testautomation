"""Texts and selectors the app repeats on many screens, kept in one place so screens cannot drift apart."""

import re

# Case-blind: toast texts are lower case in the DOM and capitalised by CSS.
RECORD_SAVED = re.compile("Record Saved Successfully", re.IGNORECASE)
RECORD_UPDATED = re.compile("Record Updated Successfully", re.IGNORECASE)
# The shared export toolbar's refusal for an empty report (sharedexportimport.ts:99-102).
EXPORT_DATA_NOT_FOUND = re.compile("Exporting data not found", re.IGNORECASE)

# The Control Room window is titled after the document whose settings it shows.
CONTROL_ROOM_SETTING_TITLE = re.compile("Sale Bill Setting|Sale Challan Setting|Sale Order Setting")

# The grids show names with non-breaking spaces.
NO_BREAK_SPACE = "\xa0"

# The list search box only has ids (or a name inside the filter bar), depending on the screen.
LIST_SEARCH_BOX = "#SearchBox, #searchItems, .searchFilterBox input[name='SearchBox']"
