// TC-014 · QA5 record - Utilities shows Data Backup · module: Masters
// Written by: QA Tester 5
// Description: QA release test of Record paste flow (qa5). Safe to delete.
import { test, expect } from '@playwright/test';
import { login } from '../helpers/mb';

test('QA5 record - Utilities shows Data Backup', async ({ page }) => {
  await page.goto('https://books6.margbooks.com/');
  await login(page);   // reads MB_USER / MB_PASS
  await page.goto('https://books6.margbooks.com/mb/utillity-menu');
  await expect(page.getByText('Data Backup')).toBeVisible();
});