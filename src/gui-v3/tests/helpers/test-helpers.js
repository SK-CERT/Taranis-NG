/**
 * Test Helper Utilities for E2E Tests
 *
 * Common functions used across multiple test suites
 */

/**
 * Login helper - authenticates user and stores credentials
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} username - Username (default: 'admin')
 * @param {string} password - Password (default: 'admin')
 */
export async function login(page, username = 'admin', password = 'admin') {
  await page.goto('/v2/login')
  await page.locator('[data-test="login-username"] input').fill(username)
  await page.locator('[data-test="login-password"] input').fill(password)
  await page.locator('[data-test="login-submit"]').click()

  // Wait for navigation to complete
  await page.waitForURL(/\/v2\/(dashboard)?$/)
}

/**
 * Logout helper
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function logout(page) {
  // Click user menu
  await page.click('[data-test="user-menu"]')
  await page.click('[data-test="logout-action"]')

  // Verify redirected to login
  await page.waitForURL('/v2/login')
}

/**
 * Navigate to configuration section
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} section - Section name (e.g., 'Roles', 'Organizations')
 */
export async function navigateToConfig(page, section) {
  // Open config sidebar if not already open
  await page.goto('/v2/config')
  await page.getByRole('navigation').getByText(section).click()
}

/**
 * Wait for notification to appear with specific text
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} expectedText - Expected notification text
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 */
export async function waitForNotification(page, expectedText, timeout = 5000) {
  const notification = page.locator('.v-snackbar')
  await notification.waitFor({ state: 'visible', timeout })
  await notification.locator(`text=${expectedText}`).waitFor({ timeout })
  return notification
}

/**
 * Wait for notification to disappear
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 */
export async function waitForNotificationDismiss(page, timeout = 5000) {
  const notification = page.locator('.v-snackbar')
  await notification.waitFor({ state: 'hidden', timeout })
}

/**
 * Open a dialog by clicking a button
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} buttonText - Button text to click (default: 'New')
 */
export async function openDialog(page, buttonText = 'New') {
  await page.getByRole('button', { name: buttonText }).click()
  await page.locator('.v-dialog').waitFor({ state: 'visible' })
}

/**
 * Close a dialog by clicking cancel or close button
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function closeDialog(page) {
  // Try close button first (X icon)
  const closeButton = page.locator('.v-dialog button:has(i.mdi-close)')
  if (await closeButton.isVisible()) {
    await closeButton.click()
  } else {
    // Otherwise try Cancel button
    await page.getByRole('button', { name: 'Cancel' }).click()
  }

  await page.locator('.v-dialog').waitFor({ state: 'hidden' })
}

/**
 * Fill form field by name
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} fieldName - Field name attribute
 * @param {string} value - Value to fill
 */
export async function fillField(page, fieldName, value) {
  await page.fill(`[name="${fieldName}"]`, value)
}

/**
 * Save form in dialog
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function saveDialog(page) {
  await page.getByRole('button', { name: 'Save' }).click()
}

/**
 * Delete an item by clicking its delete button
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} itemIdentifier - Text or locator to identify the item
 */
export async function deleteItem(page, itemIdentifier) {
  // Hover over item to show delete button
  await page.locator(`text=${itemIdentifier}`).hover()

  // Click delete button
  await page.locator(`[aria-label="Delete"]`).click()

  // Confirm deletion
  await page.getByRole('button', { name: 'Delete' }).click()
}

/**
 * Wait for page to load completely
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
export async function waitForPageLoad(page) {
  await page.waitForLoadState('networkidle')
  await page.waitForLoadState('domcontentloaded')
}

/**
 * Check if user has permission by checking if element is visible
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} selector - Element selector
 */
export async function hasPermission(page, selector) {
  try {
    await page.waitForSelector(selector, { timeout: 2000 })
    return true
  } catch {
    return false
  }
}

/**
 * Create a unique test name with timestamp
 * @param {string} baseName - Base name for the test entity
 */
export function generateTestName(baseName) {
  const timestamp = Date.now()
  return `${baseName}_${timestamp}`
}

/**
 * Take a screenshot for debugging
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} name - Screenshot name
 */
export async function takeScreenshot(page, name) {
  await page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true })
}
