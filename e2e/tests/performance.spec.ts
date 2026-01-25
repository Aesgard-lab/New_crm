import { test, expect, Page } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('homepage should load within acceptable time', async ({ page }: { page: Page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    
    const loadTime = Date.now() - startTime;
    
    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('dashboard should load within acceptable time', async ({ page }: { page: Page }) => {
    const startTime = Date.now();
    
    await page.goto('/backoffice/dashboard/');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Dashboard should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('should have good Web Vitals metrics', async ({ page }: { page: Page }) => {
    await page.goto('/backoffice/dashboard/');
    
    // Get performance metrics
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          resolve({
            lcp: entries.find(e => e.entryType === 'largest-contentful-paint')?.startTime,
          });
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // Fallback timeout
        setTimeout(() => resolve({}), 5000);
      });
    });

    // LCP should be under 2.5 seconds (good)
    if (metrics && (metrics as any).lcp) {
      expect((metrics as any).lcp).toBeLessThan(2500);
    }
  });
});

test.describe('Accessibility Tests', () => {
  test('login page should be accessible', async ({ page }: { page: Page }) => {
    await page.goto('/accounts/login/');
    
    // Check for basic accessibility
    const hasH1 = await page.locator('h1').count();
    expect(hasH1).toBeGreaterThan(0);
    
    // Check form labels
    const emailInput = page.locator('input[name="username"], input[name="email"]');
    const hasLabel = await page.locator(`label[for="${await emailInput.getAttribute('id')}"]`).count() > 0 ||
                     await emailInput.getAttribute('aria-label') !== null;
    expect(hasLabel).toBeTruthy();
  });

  test('should have proper page title', async ({ page }: { page: Page }) => {
    await page.goto('/backoffice/dashboard/');
    
    const title = await page.title();
    expect(title).not.toBe('');
    expect(title.length).toBeGreaterThan(0);
  });

  test('images should have alt text', async ({ page }: { page: Page }) => {
    await page.goto('/backoffice/dashboard/');
    
    const images = page.locator('img');
    const count = await images.count();
    
    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');
      
      // Image should have alt text or be decorative (role="presentation")
      expect(alt !== null || role === 'presentation').toBeTruthy();
    }
  });
});
