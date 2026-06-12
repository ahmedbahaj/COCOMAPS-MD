/**
 * Per-browser list of job IDs the user submitted (localStorage).
 * Public analysis URLs stay world-accessible; this list only drives "Your jobs" on the Jobs page.
 */
export const COCOMAPSMD_JOB_IDS_KEY = 'cocomapsmd:submittedJobIds'
export const COCOMAPSMD_JOB_ALIASES_KEY = 'cocomapsmd:jobAliases'

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

function getJobAliasIds(job) {
  if (!job || typeof job !== 'object') return []
  return [job.job_id, job.jobId, job.id]
    .filter((id) => typeof id === 'string' && id.length > 0)
}

export function getJobAliases() {
  try {
    const raw = localStorage.getItem(COCOMAPSMD_JOB_ALIASES_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

export function getJobAlias(job) {
  const aliases = getJobAliases()
  for (const id of getJobAliasIds(job)) {
    if (typeof aliases[id] === 'string' && aliases[id].trim()) return aliases[id]
  }
  return null
}

export function setJobAlias(job, name) {
  const cleanName = typeof name === 'string' ? name.trim() : ''
  const ids = getJobAliasIds(job)
  if (!cleanName || ids.length === 0) return false

  const aliases = getJobAliases()
  for (const id of ids) aliases[id] = cleanName
  localStorage.setItem(COCOMAPSMD_JOB_ALIASES_KEY, JSON.stringify(aliases))
  return true
}

/** Whether a merged jobs-row belongs to this browser's submitted list */
export function jobRowMatchesSubmitted(job, submittedSet) {
  if (!submittedSet || submittedSet.size === 0) return false
  if (job.job_id && submittedSet.has(job.job_id)) return true
  if (job.jobId && submittedSet.has(job.jobId)) return true
  return false
}
