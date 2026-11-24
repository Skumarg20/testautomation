// TC-012 · login · module: Auth
// Written by: QA Tester 4
import { test, expect } from '@playwright/test';
import { login } from '../helpers/mb';

test('test', async ({ page }) => {
  await page.goto('https://books6.margbooks.com/');
  await login(page);   // reads MB_USER / MB_PASS
    modifiers: ['ControlOrMeta']
  });
});