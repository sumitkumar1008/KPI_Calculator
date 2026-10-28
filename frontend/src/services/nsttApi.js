/**
 * NSTT API Client Service
 * =======================
 * Handles communication with backend NSTT analytics endpoints:
 * - /api/v1/nstt/upload
 * - /api/v1/nstt/process
 * - /api/v1/nstt/summary
 * - /api/v1/nstt/drilldown
 * - /api/v1/nstt/export
 */

import { safeParseJson } from '../utils/apiUtils'

const getApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE
  const envUrl = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL
  if (envBase) {
    return envBase.replace(/\/+$/, '')
  }
  if (envUrl) {
    return `${envUrl.replace(/\/+$/, '')}/api/v1/nstt`
  }
  return '/api/v1/nstt'
}

const API_BASE = getApiBase()

/**
 * Uploads Namo and Remedy files to backend for ingestion and VLOOKUP join.
 * @param {File} namoFile - Namo report file (CSV/XLSX)
 * @param {File} remedyFile - Remedy report file (CSV/XLSX)
 * @returns {Promise<{upload_id: string, master_response: object, stats: object, warnings: string[]}>}
 */
export async function uploadNsttFiles(namoFile, remedyFile) {
  if (!namoFile || !remedyFile) {
    throw new Error('Both Namo and Remedy files must be selected.')
  }

  const formData = new FormData()
  formData.append('namo_file', namoFile)
  formData.append('remedy_file', remedyFile)

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })

  return safeParseJson(response)
}

/**
 * Runs the NSTT Rule Engine & Aggregation on the Master Response.
 * @param {object} params - { uploadId?: string, masterResponse?: object }
 * @returns {Promise<{upload_id: string, classified_master_response: object, aggregated_result: object, processing_time_ms: number}>}
 */
export async function processNstt({ uploadId, masterResponse } = {}) {
  const payload = {}
  if (uploadId) payload.upload_id = uploadId
  if (masterResponse) payload.master_response = masterResponse

  const response = await fetch(`${API_BASE}/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return safeParseJson(response)
}

/**
 * Retrieves the aggregated hierarchical summary.
 * @param {string} uploadId - Optional upload cache UUID
 * @returns {Promise<{upload_id: string, aggregated_result: object}>}
 */
export async function getNsttSummary(uploadId) {
  const url = uploadId ? `${API_BASE}/summary?upload_id=${encodeURIComponent(uploadId)}` : `${API_BASE}/summary`
  const response = await fetch(url, {
    method: 'GET',
  })

  return safeParseJson(response)
}

/**
 * Retrieves drilldown records for a specific category node.
 * @param {object} params - { category: string, uploadId?: string, records?: object[] }
 * @returns {Promise<{category: string, total_records: number, records: object[]}>}
 */
export async function getNsttDrilldown({ category, uploadId, records } = {}) {
  if (!category) {
    throw new Error('Category path is required for drilldown query.')
  }

  const payload = { category }
  if (uploadId) payload.upload_id = uploadId
  if (records) payload.records = records

  const response = await fetch(`${API_BASE}/drilldown`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return safeParseJson(response)
}

/**
 * Triggers NSTT Excel export generation and file download.
 * @param {object} params - { uploadId?: string, masterResponse?: object, exportType?: 'dashboard' | 'raw' | 'all' }
 */
export async function exportNstt({ uploadId, masterResponse, exportType = 'all' } = {}) {
  const payload = {
    export_type: exportType,
  }
  if (uploadId) payload.upload_id = uploadId
  if (masterResponse && !uploadId) payload.master_response = masterResponse

  const response = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    await safeParseJson(response) // Will throw formatted error
  }

  // Extract filename from Content-Disposition header if present
  let filename = ''
  const disposition = response.headers.get('Content-Disposition') || ''
  const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
  if (filenameMatch && filenameMatch[1]) {
    filename = filenameMatch[1].replace(/['"]/g, '').trim()
  }
  if (!filename) {
    const ts = new Date().toISOString().slice(0, 10)
    if (exportType === 'dashboard') {
      filename = `NSTT_Dashboard_Table_${ts}.xlsx`
    } else if (exportType === 'raw') {
      filename = `NSTT_Raw_Data_VLookup_${ts}.xlsx`
    } else {
      filename = `NSTT_Output_${ts}.xlsx`
    }
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
