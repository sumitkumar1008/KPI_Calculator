/**
 * Generic API Utilities
 * =====================
 * Reusable network and response parsing utilities across domains.
 */

/**
 * Safely parses JSON response from fetch requests, handling invalid NaNs,
 * cleaning HTML error tags from backend exception traces, and formatting errors.
 *
 * @param {Response} response - Fetch response object
 * @returns {Promise<any>} - Parsed JSON object
 * @throws {Error} - Formatted error with attached metadata if response is not ok
 */
export async function safeParseJson(response) {
  const text = await response.text()
  let data

  try {
    data = JSON.parse(text)
  } catch {
    try {
      const sanitized = text.replace(/:\s*NaN\b/g, ': null')
      data = JSON.parse(sanitized)
    } catch {
      const cleanText = text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
      const preview = cleanText ? cleanText.slice(0, 150) : (response.statusText || 'Server Error')
      throw new Error(`Server Error HTTP ${response.status}: ${preview}`)
    }
  }

  if (!response.ok) {
    let msg = data?.error || data?.detail || data?.message
    if (!msg && data?.missing_columns && Array.isArray(data.missing_columns) && data.missing_columns.length > 0) {
      msg = `File Mismatch Error: Missing required column(s): ${data.missing_columns.join(', ')}`
    }
    const err = new Error(msg || `Request failed with HTTP status ${response.status}.`)
    err.errorType = data?.error_type || (data?.missing_columns?.length ? 'FILE_MISMATCH' : 'API_ERROR')
    err.dataset = data?.dataset || null
    err.filename = data?.filename || null
    err.missingColumns = Array.isArray(data?.missing_columns) ? data.missing_columns : []
    err.foundColumns = Array.isArray(data?.found_columns) ? data.found_columns : []
    err.expectedColumns = Array.isArray(data?.expected_columns) ? data.expected_columns : []
    err.internalError = data?.internal_error || data?.detail || text
    err.files = data?.files || null
    err.status = response.status
    err.data = data
    throw err
  }

  return data
}
