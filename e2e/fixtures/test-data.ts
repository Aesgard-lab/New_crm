export interface TestUser {
  email: string;
  password: string;
  name?: string;
}

export interface TestClient {
  name: string;
  email: string;
  phone?: string;
  address?: string;
}

export const TEST_USERS: Record<string, TestUser> = {
  regular: {
    email: process.env.TEST_USER_EMAIL || 'test@example.com',
    password: process.env.TEST_USER_PASSWORD || 'testpassword123',
    name: 'Test User'
  },
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || 'admin@example.com',
    password: process.env.TEST_ADMIN_PASSWORD || 'adminpassword123',
    name: 'Admin User'
  },
  staff: {
    email: process.env.TEST_STAFF_EMAIL || 'staff@example.com',
    password: process.env.TEST_STAFF_PASSWORD || 'staffpassword123',
    name: 'Staff User'
  }
};

export function generateTestClient(): TestClient {
  const timestamp = Date.now();
  return {
    name: `Test Client ${timestamp}`,
    email: `testclient${timestamp}@example.com`,
    phone: `555-${Math.floor(1000 + Math.random() * 9000)}`
  };
}

export function generateRandomEmail(): string {
  return `test${Date.now()}${Math.floor(Math.random() * 1000)}@example.com`;
}

export function generateRandomPhone(): string {
  return `555-${Math.floor(1000 + Math.random() * 9000)}`;
}
