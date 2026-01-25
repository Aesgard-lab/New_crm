import { test, expect, Page } from '@playwright/test';

test.describe('API Health Checks', () => {
  test('should return healthy status from /health/', async ({ request }) => {
    const response = await request.get('/health/');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
  });

  test('should return liveness status', async ({ request }) => {
    const response = await request.get('/health/live/');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('ok');
  });

  test('should return readiness status', async ({ request }) => {
    const response = await request.get('/health/ready/');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('ok');
  });

  test('should return ping response', async ({ request }) => {
    const response = await request.get('/health/ping/');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('pong');
  });
});

test.describe('API Documentation', () => {
  test('should load Swagger UI', async ({ page }) => {
    await page.goto('/api/docs/');
    
    // Swagger UI should load
    await expect(page.locator('.swagger-ui')).toBeVisible({ timeout: 10000 });
  });

  test('should load ReDoc', async ({ page }: { page: Page }) => {
    await page.goto('/api/redoc/');
    
    // ReDoc should load
    await expect(page.locator('[role="navigation"]')).toBeVisible({ timeout: 10000 });
  });

  test('should return OpenAPI schema', async ({ request }) => {
    const response = await request.get('/api/schema/');
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('openapi');
    expect(data).toHaveProperty('paths');
  });
});
