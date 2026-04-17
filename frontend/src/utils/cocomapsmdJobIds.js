/**
 * Per-browser list of job IDs the user submitted (localStorage).
 * Public analysis URLs stay world-accessible; this list only drives "Your jobs" on the Jobs page.
 */
export const COCOMAPSMD_JOB_IDS_KEY = 'cocomapsmd:submittedJobIds'

export function getSubmittedJobIds() {
  try {
    const raw = localStorage.getItem(COCOMAPSMD_JOB_IDS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string' && id.length > 0) : []
  } catch {
    return []
  }
}

export function addSubmittedJobId(id) {
  if (!id || typeof id !== 'string') return
  const ids = getSubmittedJobIds()
  if (ids.includes(id)) return
  ids.push(id)
  localStorage.setItem(COCOMAPSMD_JOB_IDS_KEY, JSON.stringify(ids))
}

/** Whether a merged jobs-row belongs to this browser's submitted list */
export function jobRowMatchesSubmitted(job, submittedSet) {
  if (!submittedSet || submittedSet.size === 0) return false
  if (job.job_id && submittedSet.has(job.job_id)) return true
  if (job.jobId && submittedSet.has(job.jobId)) return true
  return false
}
