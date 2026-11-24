"""Stock items that must exist in the QA tenant (ported from the original suite's chemist sale data)."""

from test_data.models import SaleItem

A_TO_Z_NS = SaleItem(
    description="A To Z Ns",
    barcode=90000001,
    itemcode=10000001,
    batch_barcode=70000001,
    multiple_barcode=12345,
    quantity=3,
    gst_percent=28,
)
BIOZENTRA = SaleItem(description="BioZentra", itemcode=10000008, quantity=5, gst_percent=5)
A_TO_Z_NS_BULK = SaleItem(description="A To Z Ns", quantity=9)

CHEMIST_SALE_ITEMS = (A_TO_Z_NS, BIOZENTRA, A_TO_Z_NS_BULK)

NEAR_EXPIRY_BIOZENTRA = SaleItem(description="BioZentra", expiry="NE", quantity=9)
EXPIRED_BIOZENTRA = SaleItem(description="BioZentra", expiry="EXP", quantity=9)
DOLO_650 = SaleItem(description="Dolo 650", itemcode=10000003, quantity=7)
BIOZENTRA_BY_BARCODE = SaleItem(description="BioZentra", barcode=900000010, quantity=2)

CHEMIST_BATCH_ITEMS = (NEAR_EXPIRY_BIOZENTRA, EXPIRED_BIOZENTRA, DOLO_650, BIOZENTRA_BY_BARCODE)
