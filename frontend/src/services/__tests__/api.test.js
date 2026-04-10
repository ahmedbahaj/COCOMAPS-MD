import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock axios before importing the module under test
vi.mock('axios', () => {
  const post = vi.fn().mockResolvedValue({ data: { success: true } })
  const create = vi.fn(() => ({ post, get: vi.fn(), interceptors: { response: { use: vi.fn() } } }))
  return { default: { create, post } }
})

// We need to test the FormData assembly logic directly
describe('uploadFileWithOptions reduce wiring', () => {
  it('sends reduce=true when useReduce is true', async () => {
    // Import after mock is set up
    const { default: apiService } = await import('../../services/api.js')

    const file = new File(['test'], 'test.pdb', { type: 'text/plain' })
    const options = {
      jobName: 'test',
      email: '',
      chain1: 'A',
      chain2: 'B',
      useReduce: true,
      interfaceCutoff: 5.0,
      waterCutoff: 5.0,
    }

    // Spy on FormData.append
    const appendSpy = vi.spyOn(FormData.prototype, 'append')

    try {
      await apiService.uploadFileWithOptions(file, options, vi.fn())
    } catch {
      // May throw due to mock; we only care about FormData construction
    }

    const reduceCalls = appendSpy.mock.calls.filter(c => c[0] === 'reduce')
    expect(reduceCalls.length).toBeGreaterThan(0)
    expect(reduceCalls[0][1]).toBe('true')

    appendSpy.mockRestore()
  })

  it('sends reduce=false when useReduce is false', async () => {
    const { default: apiService } = await import('../../services/api.js')

    const file = new File(['test'], 'test.pdb', { type: 'text/plain' })
    const options = {
      jobName: 'test',
      email: '',
      chain1: 'A',
      chain2: 'B',
      useReduce: false,
      interfaceCutoff: 5.0,
      waterCutoff: 5.0,
    }

    const appendSpy = vi.spyOn(FormData.prototype, 'append')

    try {
      await apiService.uploadFileWithOptions(file, options, vi.fn())
    } catch {
      // May throw due to mock
    }

    const reduceCalls = appendSpy.mock.calls.filter(c => c[0] === 'reduce')
    expect(reduceCalls.length).toBeGreaterThan(0)
    expect(reduceCalls[0][1]).toBe('false')

    appendSpy.mockRestore()
  })
})
