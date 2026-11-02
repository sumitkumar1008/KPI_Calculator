/**
 * Origin Private File System (OPFS) Storage & Client-Side Cache
 * ==============================================================
 * Provides high-speed, persistent browser-side storage for NSTT Master
 * and Aggregated datasets. Bypasses localStorage 5MB quota limits and
 * enables zero-server-load instant exports directly in the client.
 */

const NSTT_OPFS_PREFIX = 'nstt_cache_'

/**
 * Checks if Origin Private File System (OPFS) is supported by the current browser.
 * @returns {boolean}
 */
export function isOPFSSupported() {
  return (
    typeof navigator !== 'undefined' &&
    !!navigator.storage &&
    typeof navigator.storage.getDirectory === 'function'
  )
}

/**
 * Retrieves the OPFS root directory handle.
 * @returns {Promise<FileSystemDirectoryHandle>}
 */
async function getOPFSRoot() {
  if (!isOPFSSupported()) {
    throw new Error('Origin Private File System (OPFS) is not supported in this browser.')
  }
  return await navigator.storage.getDirectory()
}

/**
 * Saves a JSON-serializable dataset or ArrayBuffer into the browser's OPFS.
 * @param {string} key - Cache identifier (e.g. uploadId)
 * @param {object|ArrayBuffer|string} data - Dataset to persist
 */
export async function saveToOPFS(key, data) {
  if (!key) return false
  try {
    if (!isOPFSSupported()) {
      // Graceful fallback to sessionStorage for older browsers
      try {
        sessionStorage.setItem(`${NSTT_OPFS_PREFIX}${key}`, JSON.stringify(data))
        return true
      } catch {
        return false
      }
    }

    const root = await getOPFSRoot()
    const fileName = `${NSTT_OPFS_PREFIX}${key}.json`
    const fileHandle = await root.getFileHandle(fileName, { create: true })
    const writable = await fileHandle.createWritable()

    const content = typeof data === 'string' ? data : JSON.stringify(data)
    await writable.write(content)
    await writable.close()

    console.log(`[OPFS] Successfully cached dataset '${fileName}' into Browser OPFS.`)
    return true
  } catch (err) {
    console.warn('[OPFS] Failed to write dataset to OPFS:', err)
    return false
  }
}

/**
 * Reads a cached dataset from the browser's OPFS.
 * @param {string} key - Cache identifier (e.g. uploadId)
 * @returns {Promise<object|null>} Parsed JSON dataset or null
 */
export async function loadFromOPFS(key) {
  if (!key) return null
  try {
    if (!isOPFSSupported()) {
      const stored = sessionStorage.getItem(`${NSTT_OPFS_PREFIX}${key}`)
      return stored ? JSON.parse(stored) : null
    }

    const root = await getOPFSRoot()
    const fileName = `${NSTT_OPFS_PREFIX}${key}.json`
    const fileHandle = await root.getFileHandle(fileName)
    const file = await fileHandle.getFile()
    const text = await file.text()
    return JSON.parse(text)
  } catch (err) {
    // File not found or read error
    return null
  }
}

/**
 * Deletes a cached dataset from the browser's OPFS.
 * @param {string} key - Cache identifier
 */
export async function clearOPFS(key) {
  if (!key) return
  try {
    if (isOPFSSupported()) {
      const root = await getOPFSRoot()
      const fileName = `${NSTT_OPFS_PREFIX}${key}.json`
      await root.removeEntry(fileName).catch(() => {})
    } else {
      sessionStorage.removeItem(`${NSTT_OPFS_PREFIX}${key}`)
    }
  } catch {
    // Ignore cleanup errors
  }
}

/**
 * Exports data directly from OPFS to CSV entirely within the browser.
 * Zero HTTP requests to the backend server!
 * @param {Array<object>} records - Array of records to export
 * @param {string} filename - Output filename without extension
 */
export function exportToCsvFromClient(records, filename = 'nstt_export') {
  if (!Array.isArray(records) || records.length === 0) {
    throw new Error('No records available in browser cache to export.')
  }

  // Extract all distinct column keys
  const headers = Object.keys(records[0])
  const csvRows = []

  // Header row
  csvRows.push(headers.map(h => `"${String(h).replace(/"/g, '""')}"`).join(','))

  // Data rows
  for (const row of records) {
    const values = headers.map(header => {
      const val = row[header]
      if (val === null || val === undefined) return '""'
      const str = String(val).replace(/"/g, '""')
      return `"${str}"`
    })
    csvRows.push(values.join(','))
  }

  const csvString = csvRows.join('\r\n')
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

