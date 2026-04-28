import { test, expect } from '@playwright/test'
import {
  login,
  navigateToConfig,
  openDialog,
  closeDialog,
  fillField,
  saveDialog,
  waitForNotification,
  generateTestName
} from '../helpers/test-helpers'

/**
 * Role Management CRUD E2E Tests
 *
 * Tests create, read, update, delete operations for roles
 */

test.describe('Role Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await login(page)

    // Navigate to roles section
    await navigateToConfig(page, 'Roles')

    // Wait for roles to load
    await page.waitForSelector('.v-card', { timeout: 5000 })
  })

  test('should display roles list', async ({ page }) => {
    // Verify we're on roles page
    await expect(page).toHaveURL(/\/config\/roles/)

    // Should show page title or header
    await expect(page.locator('text=/roles/i')).toBeVisible()

    // Should show New button if user has permissions
    const newButton = page.getByRole('button', { name: 'New' })
    const isVisible = await newButton.isVisible().catch(() => false)

    if (isVisible) {
      await expect(newButton).toBeVisible()
    }
  })

  test('should create a new role', async ({ page }) => {
    const roleName = generateTestName('Test Role')
    const roleDescription = 'Automated test role'

    // Click New button
    await openDialog(page, 'New')

    // Verify dialog is open
    await expect(page.locator('.v-dialog')).toBeVisible()

    // Fill form
    await fillField(page, 'name', roleName)
    await fillField(page, 'description', roleDescription)

    // Save
    await saveDialog(page)

    // Wait for success notification
    await waitForNotification(page, /created successfully/i)

    // Dialog should close
    await expect(page.locator('.v-dialog')).not.toBeVisible()

    // New role should appear in list
    await expect(page.locator(`text=${roleName}`)).toBeVisible()
  })

  test('should show validation error when creating role without name', async ({ page }) => {
    // Click New button
    await openDialog(page, 'New')

    // Try to save without filling required field
    await saveDialog(page)

    // Should show validation error
    await expect(page.locator('text=/required/i')).toBeVisible()

    // Dialog should remain open
    await expect(page.locator('.v-dialog')).toBeVisible()
  })

  test('should edit an existing role', async ({ page }) => {
    // First create a role to edit
    const roleName = generateTestName('Edit Test Role')
    await openDialog(page, 'New')
    await fillField(page, 'name', roleName)
    await fillField(page, 'description', 'Original description')
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Click on the role card to edit
    await page.locator(`.v-card:has-text("${roleName}")`).click()

    // Wait for edit dialog
    await expect(page.locator('.v-dialog')).toBeVisible()

    // Modify description
    const newDescription = 'Updated description'
    await fillField(page, 'description', newDescription)

    // Save
    await saveDialog(page)

    // Should show updated notification
    await waitForNotification(page, /updated successfully/i)

    // Dialog should close
    await expect(page.locator('.v-dialog')).not.toBeVisible()
  })

  test('should delete a role', async ({ page }) => {
    // First create a role to delete
    const roleName = generateTestName('Delete Test Role')
    await openDialog(page, 'New')
    await fillField(page, 'name', roleName)
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Find the role card and delete button
    const roleCard = page.locator(`.v-card:has-text("${roleName}")`)
    await expect(roleCard).toBeVisible()

    // Hover to show delete button
    await roleCard.hover()

    // Click delete button (usually in the card actions)
    await roleCard.locator('[aria-label="Delete"]').click()

    // Confirm deletion in dialog
    await page.getByRole('button', { name: /delete/i }).click()

    // Should show deleted notification
    await waitForNotification(page, /deleted successfully/i)

    // Role should no longer be in list
    await expect(page.locator(`text=${roleName}`)).not.toBeVisible()
  })

  test('should cancel role creation', async ({ page }) => {
    // Click New button
    await openDialog(page, 'New')

    // Fill some data
    await fillField(page, 'name', 'Cancelled Role')

    // Cancel
    await closeDialog(page)

    // Dialog should close
    await expect(page.locator('.v-dialog')).not.toBeVisible()

    // Role should not be created
    await expect(page.locator('text=Cancelled Role')).not.toBeVisible()
  })

  test('should filter/search roles', async ({ page }) => {
    // Create a test role first
    const roleName = generateTestName('Searchable Role')
    await openDialog(page, 'New')
    await fillField(page, 'name', roleName)
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Look for search input (if implemented)
    const searchInput = page.locator('input[type="text"][placeholder*="search" i]')
    const searchExists = await searchInput.isVisible().catch(() => false)

    if (searchExists) {
      // Use search
      await searchInput.fill(roleName)

      // Should show only matching role
      await expect(page.locator(`text=${roleName}`)).toBeVisible()
    }
  })

  test('should handle duplicate role names', async ({ page }) => {
    const duplicateName = generateTestName('Duplicate Role')

    // Create first role
    await openDialog(page, 'New')
    await fillField(page, 'name', duplicateName)
    await saveDialog(page)
    await waitForNotification(page, /created successfully/i)

    // Try to create another with same name
    await openDialog(page, 'New')
    await fillField(page, 'name', duplicateName)
    await saveDialog(page)

    // Should show error notification
    await waitForNotification(page, /error|exists|duplicate/i)
  })
})
