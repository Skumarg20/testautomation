// TC-015 · QA4 written smoke 191010 · module: Sale
// Written by: QA Tester 4
// Description: edited after reopen
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('QA4 written smoke 191010', async ({ page }) => {
  // Log in
  await login(page);
  // Open Sale Bill
  await openScreen(page, 'sale_bill');
  // Verify "Sale"
  await expect(page.getByText('Sale')).toBeVisible();
});
