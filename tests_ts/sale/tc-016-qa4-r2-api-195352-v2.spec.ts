// TC-016 · QA4 R2 api 195352 v2 · module: Sale
// Written by: QA Tester 4
// Description: R2 UI resave
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('QA4 R2 api 195352 v2', async ({ page }) => {
  // Log in
  await login(page);
  // Open Sale Bill
  await openScreen(page, 'sale_bill');
});
