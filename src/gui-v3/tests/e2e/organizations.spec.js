import { test, expect } from '@playwright/test'
import {
  login,
  navigateToConfig,
  openDialog,
  fillField,
  saveDialog,
  waitForNotification,
  generateTestName
} from '../helpers/test-helpers'

/**
 * Organization Management CRUD E2E Tests
 *
 * Template for testing CRUD operations on other entities
 * Can be replicated for: ACLs, ProductTypes, Attributes, ReportTypes,
 * OSINTSources, OSINTSourceGroups, Collectors, DataProviders, etc.
 */

test.describe('Organization Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await navigateToConfig(page, 'Organizations')
    await page.waitForSelector('.v-card', { timeout: 5000 })
  })

  test('should display organizations list', async ({ page }) => {
    await expect(page).toHaveURL(/\/config\/organizations/)
    await expect(page.locator('text=/organizations/i')).toBeVisible()
  })

  test('should create a new organization', async ({ page }) => {
    const orgName = generateTestName('Test Org')
    const orgDescription = 'Automated test organization'

    await openDialog(page, 'New')
    await expect(page.locator('.v-dialog')).toBeVisible()

    await fillField(page, 'name', orgName)
    await fillField(page, 'description', orgDescription)

    // Fill additional organization-specific fields if needed
    // await fillField(page, 'street', '123 Test St')
    // await fillField(page, 'city', 'Test City')

    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    await expect(page.locator('.v-dialog')).not.toBeVisible()
    await expect(page.locator(`text=${orgName}`)).toBeVisible()
  })

  test('should require name field', async ({ page }) => {
    await openDialog(page, 'New')
    await fillField(page, 'description', 'Description without name')
    await saveDialog(page)

    await expect(page.locator('text=/required/i')).toBeVisible()
    await expect(page.locator('.v-dialog')).toBeVisible()
  })

  test('should edit organization', async ({ page }) => {
    const orgName = generateTestName('Edit Org')

    // Create organization
    await openDialog(page, 'New')
    await fillField(page, 'name', orgName)
    await fillField(page, 'description', 'Original description')
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Edit organization
    await page.locator(`.v-card:has-text("${orgName}")`).click()
    await expect(page.locator('.v-dialog')).toBeVisible()

    const newDescription = 'Updated description ' + Date.now()
    await fillField(page, 'description', newDescription)
    await saveDialog(page)

    await waitForNotification(page, /updated successfully/i)
    await expect(page.locator('.v-dialog')).not.toBeVisible()
  })

  test('should delete organization', async ({ page }) => {
    const orgName = generateTestName('Delete Org')

    // Create organization
    await openDialog(page, 'New')
    await fillField(page, 'name', orgName)
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Delete organization
    const orgCard = page.locator(`.v-card:has-text("${orgName}")`)
    await orgCard.hover()
    await orgCard.locator('[aria-label="Delete"]').click()
    await page.getByRole('button', { name: /delete/i }).click()

    await waitForNotification(page, /deleted successfully/i)
    await expect(page.locator(`text=${orgName}`)).not.toBeVisible()
  })

  test('should cancel creation', async ({ page }) => {
    await openDialog(page, 'New')
    await fillField(page, 'name', 'Cancelled Organization')

    // Click cancel or close
    await page.locator('.v-dialog button:has(i.mdi-close)').click()

    await expect(page.locator('.v-dialog')).not.toBeVisible()
    await expect(page.locator('text=Cancelled Organization')).not.toBeVisible()
  })
})

/**
 * TEMPLATE: Copy this file to test other CRUD entities
 *
 * 1. Copy this file: cp organizations.spec.js product-types.spec.js
 * 2. Update entity name: Organizations → ProductTypes
 * 3. Update navigation: 'Organizations' → 'Product Types'
 * 4. Update URL pattern: /organizations/ → /product-types/
 * 5. Update field names to match entity schema
 * 6. Add entity-specific validations
 *
 * Entities to test (22 total):
 * - ✅ Roles
 * - ✅ Organizations
 * - ⏳ ACL Entries
 * - ⏳ Product Types
 * - ⏳ Attributes
 * - ⏳ Report Types
 * - ⏳ OSINT Sources
 * - ⏳ OSINT Source Groups
 * - ⏳ Collectors Nodes
 * - ⏳ Data Providers
 * - ⏳ Presenters Nodes
 * - ⏳ Publishers Nodes
 * - ⏳ Remote Accesses
 * - ⏳ Remote Nodes
 * - ⏳ Asset Groups
 * - ⏳ External Users
 * - ⏳ Notification Templates
 * - ⏳ Bots Nodes
 * - ⏳ Bot Presets
 * - ⏳ Publisher Presets
 * - ⏳ Users
 * - ⏳ Word Lists
 */
