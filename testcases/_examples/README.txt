==========================================================
  NAMOONE KE TEST CASE
==========================================================

Ye files .example par khatam hoti hain, isliye tool inhe LOAD NAHI karta.
Ye yahan sirf dekhne ke liye hain -- ki ek test kaise likha jata hai.

Kisi ko use karna ho to:
  1. file copy karo
  2. .example hata do (03_sales.yaml.example -> 03_sales.yaml)
  3. andar ke item ke naam, barcode, party apne data ke hisaab se badlo
  4. ui.bat me wo case dikhne lagega

DHYAAN: inme jo item/barcode/party likhe hain wo MERE andaze hain --
"Sample Item", "80000111", "Cash Account". Tumhare data me ye ho bhi
sakte hain aur nahi bhi. Bina badle chalane par wo fail honge, aur wo
app ka bug nahi hoga.

----------------------------------------------------------
  KYA-KYA HAI
----------------------------------------------------------
  02_masters.yaml.example       Item aur Ledger banana
  03_sales.yaml.example         Sale Bill -- trade ke hisaab se badalta hai
  04_inventory_purchase.yaml.example   Purchase aur stock
  05_gst_reports.yaml.example   GSTR-1 (draft -- screen ka naksha nahi bana)
  06_search.yaml.example        Item/Ledger search
  07_pharma.yaml.example        Patient, Doctor, Batch, Expiry
  08_retail.yaml.example        Counter Sale -- party poochta hai ya nahi

----------------------------------------------------------
  SIRF LOGIN KE CASE BUNDLED HAIN
----------------------------------------------------------
testcases/01_auth.yaml me char case hain. Wo isliye rakhe hain kyunki
login ke bina koi bhi test chal hi nahi sakta -- wo tumhare setup ki
jaanch bhi kar dete hain.

Baaki sab tum khud likhoge, apne data ke hisaab se. Yahi sahi hai:
mere likhe case mere andaze the, tumhare case tumhare asli data par
honge.
