import { Page, Locator, expect } from '@playwright/test';

export class ClientsPage {
  readonly page: Page;
  readonly title: Locator;
  readonly searchInput: Locator;
  readonly addClientButton: Locator;
  readonly clientsTable: Locator;
  readonly clientRows: Locator;
  readonly pagination: Locator;
  readonly filterButton: Locator;
  readonly exportButton: Locator;

  // Modal elements
  readonly modal: Locator;
  readonly modalTitle: Locator;
  readonly modalClose: Locator;

  // Form elements
  readonly nameInput: Locator;
  readonly emailInput: Locator;
  readonly phoneInput: Locator;
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.title = page.locator('h1, .page-title');
    this.searchInput = page.locator('input[type="search"], input[name="search"], .search-input');
    this.addClientButton = page.locator('a[href*="create"], button:has-text("Nuevo"), button:has-text("Agregar")');
    this.clientsTable = page.locator('table, .clients-list');
    this.clientRows = page.locator('table tbody tr, .client-item');
    this.pagination = page.locator('.pagination');
    this.filterButton = page.locator('button:has-text("Filtrar"), .filter-btn');
    this.exportButton = page.locator('button:has-text("Exportar"), a:has-text("Exportar")');

    // Modal
    this.modal = page.locator('.modal, [role="dialog"]');
    this.modalTitle = page.locator('.modal-title, [role="dialog"] h2');
    this.modalClose = page.locator('.modal .close, [role="dialog"] button[aria-label="Close"]');

    // Form
    this.nameInput = page.locator('input[name="name"], input[name="first_name"]');
    this.emailInput = page.locator('input[name="email"]');
    this.phoneInput = page.locator('input[name="phone"], input[name="telefono"]');
    this.saveButton = page.locator('button[type="submit"], button:has-text("Guardar")');
    this.cancelButton = page.locator('button:has-text("Cancelar"), a:has-text("Cancelar")');
  }

  async goto() {
    await this.page.goto('/clients/');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.page.keyboard.press('Enter');
    await this.page.waitForLoadState('networkidle');
  }

  async clickAddClient() {
    await this.addClientButton.click();
  }

  async fillClientForm(data: { name: string; email: string; phone?: string }) {
    await this.nameInput.fill(data.name);
    await this.emailInput.fill(data.email);
    if (data.phone) {
      await this.phoneInput.fill(data.phone);
    }
  }

  async saveClient() {
    await this.saveButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  async getClientCount() {
    return await this.clientRows.count();
  }

  async clickClientByName(name: string) {
    await this.page.locator(`tr:has-text("${name}"), .client-item:has-text("${name}")`).click();
  }
}
