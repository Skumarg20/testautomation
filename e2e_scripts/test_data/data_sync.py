"""Data for the data sync journey (J35) that is not on the shared QA companies.

DS-18, DS-19 and DS-45 write `tbldataSyncRequest` for a company for good (a cancelled request can never be
sent again, `OfflineOnlineDataSync.cs:2090-2113`), so they run only on a company kept for that purpose on
the chemist login. The tests look for it at run time and skip when it is not there; create it by hand (any
business type) and never use it for anything else.
"""

THROWAWAY_COMPANY = "QA Data Sync Throwaway"
