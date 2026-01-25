import { Page, Locator } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly title: Locator;
  readonly userMenu: Locator;
  readonly logoutButton: Locator;
  readonly sidebar: Locator;
  readonly mainContent: Locator;

  // Navigation items
  readonly clientsLink: Locator;
  readonly activitiesLink: Locator;
  readonly membershipsLink: Locator;
  readonly reportsLink: Locator;
  readonly settingsLink: Locator;

  // Dashboard widgets
  readonly statsCards: Locator;
  readonly recentActivity: Locator;
  readonly quickActions: Locator;

  constructor(page: Page) {
    this.page = page;
    this.title = page.locator('h1, .dashboard-title');
    this.userMenu = page.locator('.user-menu, .dropdown-toggle, [data-toggle="dropdown"]');
    this.logoutButton = page.locator('a[href*="logout"], button:has-text("Logout"), button:has-text("Cerrar")');
    this.sidebar = page.locator('.sidebar, nav.main-nav');
    this.mainContent = page.locator('.main-content, main, .content');

    // Navigation
    this.clientsLink = page.locator('a[href*="clients"], a:has-text("Clientes")');
    this.activitiesLink = page.locator('a[href*="activities"], a:has-text("Actividades")');
    this.membershipsLink = page.locator('a[href*="memberships"], a:has-text("Membresias")');
    this.reportsLink = page.locator('a[href*="reports"], a:has-text("Reportes")');
    this.settingsLink = page.locator('a[href*="settings"], a:has-text("Configuracion")');

    // Widgets
    this.statsCards = page.locator('.stats-card, .stat-widget, .dashboard-stat');
    this.recentActivity = page.locator('.recent-activity, .activity-feed');
    this.quickActions = page.locator('.quick-actions, .action-buttons');
  }

  async goto() {
    await this.page.goto('/backoffice/dashboard/');
  }

  async navigateToClients() {
    await this.clientsLink.click();
    await this.page.waitForURL('**/clients/**');
  }

  async navigateToActivities() {
    await this.activitiesLink.click();
    await this.page.waitForURL('**/activities/**');
  }

  async logout() {
    await this.userMenu.click();
    await this.logoutButton.click();
  }
}
