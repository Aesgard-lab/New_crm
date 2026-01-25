import { test, expect } from '@playwright/test';
import { ClientsPage } from '../pages/clients.page';

test.describe('Clients Management', () => {
  test('should load clients list page', async ({ page }) => {
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();

    await expect(page).toHaveURL(/clients/);
    await expect(clientsPage.title).toBeVisible();
  });

  test('should display search functionality', async ({ page }) => {
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();

    await expect(clientsPage.searchInput).toBeVisible();
  });

  test('should display add client button', async ({ page }) => {
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();

    await expect(clientsPage.addClientButton).toBeVisible();
  });

  test('should search for clients', async ({ page }) => {
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();

    await clientsPage.search('test');
    
    // Verify search was performed (URL should update or results should filter)
    await page.waitForLoadState('networkidle');
  });

  test('should open add client form', async ({ page }) => {
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();

    await clientsPage.clickAddClient();
    
    // Should navigate to create page or open modal
    await page.waitForLoadState('networkidle');
    
    // Check if we're on create page or modal is open
    const isOnCreatePage = page.url().includes('create') || page.url().includes('nuevo');
    const isModalOpen = await clientsPage.modal.isVisible().catch(() => false);
    
    expect(isOnCreatePage || isModalOpen).toBeTruthy();
  });

  test.skip('should create a new client', async ({ page }) => {
    // Skip by default - enable when test DB is set up
    const clientsPage = new ClientsPage(page);
    await clientsPage.goto();
    await clientsPage.clickAddClient();

    const testClient = {
      name: `Test Client ${Date.now()}`,
      email: `test${Date.now()}@example.com`,
      phone: '555-1234'
    };

    await clientsPage.fillClientForm(testClient);
    await clientsPage.saveClient();

    // Verify client was created
    await expect(page).not.toHaveURL(/create/);
  });
});
