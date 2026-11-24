// TC-026 · QA4 R4 api 221159 v2 · module: Sale
// Written by: QA Tester 4
// Description: R4 UI resave desc
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('QA4 R4 api 221159 v2', async ({ page }) => {
  // Log in
  await login(page);
  // Open Sale Bill
  await openScreen(page, 'sale_bill');
  // Verify "Sale"
  await expect(page.getByText('Sale')).toBeVisible();
});
