// TC-022 · QA4 R3 ghost 211756 · module: Sale
// Written by: QA Tester 4
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('t', async ({ page }) => {
  await login(page);
  await openScreen(page, 'sale_bill');
});
