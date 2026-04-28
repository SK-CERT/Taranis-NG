/**
 * Centralized API mock helpers for Vitest.
 *
 * Provides factories for mocking the Axios-based ApiService and individual
 * API modules so that store / composable tests never hit the network.
 */
import { vi } from 'vitest'

/**
 * Create a mock for `@/services/api_service`.
 * Returns an object whose methods are all `vi.fn()` stubs.
 *
 * @returns {Object} — mock ApiService
 */
export function createMockApiService() {
  return {
    init: vi.fn(),
    setHeader: vi.fn(),
    get: vi.fn().mockResolvedValue({ data: {} }),
    getWithCancel: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
    upload: vi.fn().mockResolvedValue({ data: {} }),
    download: vi.fn().mockResolvedValue(null)
  }
}

/**
 * Helper to create a mock that resolves with `{ data: payload }`.
 * Matches the shape of Axios responses used throughout the codebase.
 *
 * @param {*} payload - data to return inside `response.data`
 * @returns {import('vitest').Mock}
 */
export function mockApiResponse(payload) {
  return vi.fn().mockResolvedValue({ data: payload })
}

/**
 * Helper to create a mock that rejects with an error.
 *
 * @param {string} [message='Request failed']
 * @param {number} [status=500]
 * @returns {import('vitest').Mock}
 */
export function mockApiError(message = 'Request failed', status = 500) {
  const error = new Error(message)
  error.response = { status, data: { error: message } }
  return vi.fn().mockRejectedValue(error)
}
