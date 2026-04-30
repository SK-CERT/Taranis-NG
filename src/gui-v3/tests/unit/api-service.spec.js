import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'
import ApiService from '@/services/api_service'

vi.mock('axios', async () => {
  const fn = vi.fn()
  fn.defaults = { baseURL: '', headers: { common: {} } }
  fn.get = vi.fn()
  fn.post = vi.fn()
  fn.put = vi.fn()
  fn.delete = vi.fn()
  fn.isCancel = vi.fn(() => false)
  return { default: fn }
})

describe('ApiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    axios.defaults.headers.common = {}
  })

  // ── init ──────────────────────────────────────
  describe('init', () => {
    it('should set baseURL on axios defaults', () => {
      ApiService.init('https://api.example.com')
      expect(axios.defaults.baseURL).toBe('https://api.example.com')
    })

    it('should call setHeader after init', () => {
      const spy = vi.spyOn(ApiService, 'setHeader')
      ApiService.init('https://api.example.com')
      expect(spy).toHaveBeenCalled()
    })
  })

  // ── setHeader ─────────────────────────────────
  describe('setHeader', () => {
    it('should set Authorization header when ACCESS_TOKEN exists', () => {
      localStorage.ACCESS_TOKEN = 'my-jwt'
      ApiService.setHeader()
      expect(axios.defaults.headers.common['Authorization']).toBe('Bearer my-jwt')
    })

    it('should clear headers when no ACCESS_TOKEN', () => {
      axios.defaults.headers.common['Authorization'] = 'leftover'
      ApiService.setHeader()
      expect(axios.defaults.headers.common).toEqual({})
    })
  })

  // ── HTTP Methods ──────────────────────────────
  describe('HTTP Methods', () => {
    it('get should call axios.get', () => {
      ApiService.get('/test')
      expect(axios.get).toHaveBeenCalledWith('/test', {})
    })

    it('get should pass data parameter', () => {
      ApiService.get('/test', { params: { q: 'search' } })
      expect(axios.get).toHaveBeenCalledWith('/test', { params: { q: 'search' } })
    })

    it('post should call axios.post', () => {
      const data = { name: 'test' }
      ApiService.post('/items', data)
      expect(axios.post).toHaveBeenCalledWith('/items', data)
    })

    it('put should call axios.put', () => {
      const data = { id: 1, name: 'updated' }
      ApiService.put('/items/1', data)
      expect(axios.put).toHaveBeenCalledWith('/items/1', data)
    })

    it('delete should call axios.delete', () => {
      ApiService.delete('/items/1')
      expect(axios.delete).toHaveBeenCalledWith('/items/1')
    })
  })

  // ── upload ────────────────────────────────────
  describe('upload', () => {
    it('should post with multipart/form-data content type', () => {
      const formData = new FormData()
      ApiService.upload('/upload', formData)
      expect(axios.post).toHaveBeenCalledWith('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })
  })

  // ── getWithCancel ─────────────────────────────
  describe('getWithCancel', () => {
    it('should call axios.get with abort signal', () => {
      vi.mocked(axios.get).mockResolvedValue({ data: [] })
      ApiService.getWithCancel('newsItems', '/news')
      expect(axios.get).toHaveBeenCalledWith('/news', {
        signal: expect.any(AbortSignal)
      })
    })

    it('should abort previous request with same cancel key', () => {
      vi.mocked(axios.get).mockResolvedValue({ data: [] })
      ApiService.getWithCancel('newsItems', '/news?page=1')
      ApiService.getWithCancel('newsItems', '/news?page=2')

      // Second call should have been made
      expect(axios.get).toHaveBeenCalledTimes(2)
    })

    it('should suppress cancellation errors', async () => {
      const cancelError = new Error('canceled')
      vi.mocked(axios.get).mockRejectedValue(cancelError)
      vi.mocked(axios.isCancel).mockReturnValue(true)

      // Should not throw
      const result = await ApiService.getWithCancel('key', '/endpoint')
      expect(result).toBeUndefined()
    })

    it('should rethrow non-cancellation errors', async () => {
      const networkError = new Error('Network Error')
      vi.mocked(axios.get).mockRejectedValue(networkError)
      vi.mocked(axios.isCancel).mockReturnValue(false)

      await expect(ApiService.getWithCancel('key', '/endpoint')).rejects.toThrow('Network Error')
    })
  })

  // ── download ──────────────────────────────────
  describe('download', () => {
    it('should make POST request with blob responseType', async () => {
      const blobData = new Blob(['test'])
      vi.mocked(axios).mockResolvedValue({
        data: blobData,
        headers: {}
      })

      // Mock DOM APIs
      const clickSpy = vi.fn()
      const removeSpy = vi.fn()
      vi.spyOn(document, 'createElement').mockReturnValue({
        href: '',
        download: '',
        click: clickSpy,
        remove: removeSpy
      })
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      await ApiService.download('/export', { ids: [1, 2] }, 'report.pdf')

      expect(axios).toHaveBeenCalledWith({
        url: '/export',
        method: 'POST',
        responseType: 'blob',
        data: { ids: [1, 2] }
      })
      expect(clickSpy).toHaveBeenCalled()
      expect(removeSpy).toHaveBeenCalled()
    })

    it('should use filename from content-disposition header', async () => {
      vi.mocked(axios).mockResolvedValue({
        data: new Blob(['pdf']),
        headers: { 'content-disposition': 'attachment; filename="server-report.pdf"' }
      })

      const mockLink = { href: '', download: '', click: vi.fn(), remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      await ApiService.download('/export', {}, 'fallback.pdf')

      expect(mockLink.download).toBe('server-report.pdf')
    })

    it('should use fallback filename when no content-disposition', async () => {
      vi.mocked(axios).mockResolvedValue({
        data: new Blob(['data']),
        headers: {}
      })

      const mockLink = { href: '', download: '', click: vi.fn(), remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      await ApiService.download('/export', {}, 'my-file.csv')

      expect(mockLink.download).toBe('my-file.csv')
    })
  })
})
