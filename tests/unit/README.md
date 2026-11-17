# Offline tests -- browser ki zaroorat nahi

Ye khud FRAMEWORK ko test karte hain, MargBooks ko nahi. Isliye ye bina
internet, bina login, 1 second me chalte hain.

    unit-tests.bat

Kya check karte hain:
  test_safety_rules.py         delete-guard ke niyam sahi hain? netguard kaunsi
                               request rokta hai?
  test_framework_logic.py      test case library valid hai? placeholder chalte
                               hain? data likhne wale case destructive mark hain?
  test_pom_contracts.py        page object apna waada nibha rahe hain?
  test_click_guard_coverage.py koi click guard ke bina to nahi reh gaya?

Aakhri wala khaas hai: wo code review ko HAMESHA ke liye pakka kar deta hai.
Kal koi naya raw .click() likhega to ye turant fail hoga.
