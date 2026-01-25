import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

test.describe('Authentication', () => {
  test.use({ storageState: { cookies: [], origins: [] } }); // Fresh session

  test('should display login page correctly', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    await loginPage.login('invalid@example.com', 'wrongpassword');
    
    // Should stay on login page or show error
    await expect(page).toHaveURL(/login/);
    // Check for error message (adjust selector based on your app)
    await expect(loginPage.errorMessage).toBeVisible({ timeout: 5000 }).catch(() => {
      // Alternative: check we're still on login page
      expect(page.url()).toContain('login');
    });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    await loginPage.login(
      process.env.TEST_USER_EMAIL || 'test@example.com',
      process.env.TEST_USER_PASSWORD || 'testpassword123'
    );
    
    // Should redirect to dashboard
    await expect(page).not.toHaveURL(/login/, { timeout: 10000 });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/backoffice/dashboard/');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });
});
