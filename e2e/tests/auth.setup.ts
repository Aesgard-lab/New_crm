import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto('/accounts/login/');

  // Fill login form
  await page.fill('input[name="username"], input[name="email"]', process.env.TEST_USER_EMAIL || 'test@example.com');
  await page.fill('input[name="password"]', process.env.TEST_USER_PASSWORD || 'testpassword123');
  
  // Submit form
  await page.click('button[type="submit"]');

  // Wait for navigation to complete
  await page.waitForURL('**/dashboard/**', { timeout: 10000 });

  // Verify login was successful
  await expect(page).not.toHaveURL('**/login/**');

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
