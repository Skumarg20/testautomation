// TC-018 · QA4 R2 dbl 201427 · module: General
// Written by: QA Tester 4
// Description: Log in → Open Sale Bill
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('QA4 R2 dbl 201427', async ({ page }) => {
  // Log in
  await login(page);
  // Open Sale Bill
  await openScreen(page, 'sale_bill');
});
