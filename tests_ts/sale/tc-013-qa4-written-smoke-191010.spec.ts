// TC-013 · QA4 written smoke 191010 · module: Sale
// Written by: QA Tester 4
// Description: QA4 smoke: log in and open Sale Bill
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('test', async ({ page }) => {
  // Log in
  await login(page);
  // Open Sale Bill
  await openScreen(page, 'sale_bill');
});
