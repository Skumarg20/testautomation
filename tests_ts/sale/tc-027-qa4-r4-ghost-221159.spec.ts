// TC-027 · QA4 R4 ghost 221159 · module: Sale
// Written by: QA Tester 4
import { test, expect } from '@playwright/test';
import { login, openScreen } from '../helpers/mb';

test('t', async ({ page }) => {
  await login(page);
  await openScreen(page, 'sale_bill');
});
