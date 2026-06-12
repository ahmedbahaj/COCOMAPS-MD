import { beforeEach, describe, expect, it } from 'vitest'

import {
  COCOMAPSMD_JOB_ALIASES_KEY,
  getJobAlias,
  setJobAlias
} from '../cocomapsmdJobIds.js'

describe('browser-local job aliases', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('stores an alias under every stable identifier for a job', () => {
    const job = { id: 'system-dir', job_id: 'upload-uuid', jobId: 'public-id' }

    expect(setJobAlias(job, 'My private alias')).toBe(true)
    expect(getJobAlias(job)).toBe('My private alias')

    const stored = JSON.parse(localStorage.getItem(COCOMAPSMD_JOB_ALIASES_KEY))
    expect(stored['system-dir']).toBe('My private alias')
    expect(stored['upload-uuid']).toBe('My private alias')
    expect(stored['public-id']).toBe('My private alias')
  })

  it('does not store an empty alias', () => {
    expect(setJobAlias({ id: 'system-dir' }, '   ')).toBe(false)
    expect(localStorage.getItem(COCOMAPSMD_JOB_ALIASES_KEY)).toBeNull()
  })
})
