import { afterEach, describe, expect, it, vi } from 'vitest'
import { get } from './client'

afterEach(() => vi.restoreAllMocks())

describe('API client', () => {
  it('requests JSON with credentials', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ok:true}), {status:200,headers:{'Content-Type':'application/json'}}))
    const result = await get<{ok:boolean}>('/api/test')
    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalled()
    expect(fetchMock.mock.calls[0][1]?.credentials).toBe('include')
  })
})
