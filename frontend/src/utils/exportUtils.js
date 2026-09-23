/**
 * Utilities for exporting table and chart data to Excel, CSV, and PNG
 */

/**
 * Sends a POST request to backend export API and triggers browser file download.
 * @param {Object} options
 * @param {'xlsx'|'csv'} options.format - File format
 * @param {string} options.filename - Desired file name without extension
 * @param {string} [options.title] - Report title
 * @param {string} [options.sheetName] - Worksheet name for Excel
 * @param {Array<{key: string, label: string}>} options.columns - Column specifications
 * @param {Array<Object>} options.data - Data rows
 */
export async function exportDataViaApi({
  format = 'xlsx',
  filename = 'kpi_export',
  title = '',
  sheetName = 'Sheet1',
  columns = [],
  data = [],
}) {
  if (!Array.isArray(data) || data.length === 0) {
    throw new Error('No data available to export.')
  }

  const endpoint = import.meta.env.VITE_API_ENDPOINT
    ? `${import.meta.env.VITE_API_ENDPOINT.replace(/\/kpi\/upload\/?$/, '')}/kpi/export`
    : '/api/v1/kpi/export'

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      format,
      filename,
      title,
      sheet_name: sheetName,
      columns,
      data,
    }),
  })

  if (!response.ok) {
    let errorMsg = `Server error HTTP ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson?.error) errorMsg = errJson.error
    } catch {
      // ignore
    }
    throw new Error(errorMsg)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${filename}.${format}`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

/**
 * Downloads directly from the backend server-side in-memory cache without sending rows over network.
 * @param {Object} options
 * @param {'avg'|'automation_run'|'automation_rca'|'raw'|'bucket'} [options.tableType='avg'] - Dataset type
 * @param {'monthly'|'weekly'|'daily'} [options.period='monthly'] - Aggregation period
 * @param {'xlsx'|'csv'} [options.format='xlsx'] - File format
 * @param {string} [options.uploadId] - Optional upload session ID
 * @param {string} [options.filename] - Custom output filename
 */
export async function exportFromCacheApi({
  tableType = 'avg',
  period = 'monthly',
  format = 'xlsx',
  uploadId = null,
  filename = '',
}) {
  const base = import.meta.env.VITE_API_ENDPOINT
    ? `${import.meta.env.VITE_API_ENDPOINT.replace(/\/kpi\/upload\/?$/, '')}/kpi/export/cache`
    : '/api/v1/kpi/export/cache'

  const params = new URLSearchParams({
    type: tableType,
    period,
    format,
  })
  if (uploadId) params.append('upload_id', uploadId)
  if (filename) params.append('filename', filename)

  const response = await fetch(`${base}?${params.toString()}`)
  if (!response.ok) {
    let errorMsg = `Server error HTTP ${response.status}`
    try {
      const errJson = await response.json()
      if (errJson?.error) errorMsg = errJson.error
    } catch {
      // ignore
    }
    throw new Error(errorMsg)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${filename || `${tableType}_${period}`}.${format}`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

/**
 * Exports an SVG element (e.g. from Recharts) as a high-resolution PNG image.
 * @param {SVGElement|HTMLElement} containerOrSvg - SVG or container holding the SVG
 * @param {string} filename - Filename without extension
 * @param {string} [title] - Optional title for the image
 */
export function exportSvgAsPng(containerOrSvg, filename = 'chart') {
  return new Promise((resolve, reject) => {
    try {
      let svg = containerOrSvg
      if (containerOrSvg && !(containerOrSvg instanceof SVGElement)) {
        svg = containerOrSvg.querySelector('svg')
      }

      if (!svg) {
        throw new Error('Chart SVG element not found for export.')
      }

      const rect = svg.getBoundingClientRect()
      const width = rect.width || 800
      const height = rect.height || 400
      const scale = 2 // 2x for sharp retina output

      // Clone SVG and ensure XML namespaces and dimensions
      const clonedSvg = svg.cloneNode(true)
      clonedSvg.setAttribute('width', width)
      clonedSvg.setAttribute('height', height)
      clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')

      // Inline computed styles for critical text elements
      const allText = clonedSvg.querySelectorAll('text')
      const origText = svg.querySelectorAll('text')
      allText.forEach((t, i) => {
        if (origText[i]) {
          const style = window.getComputedStyle(origText[i])
          t.setAttribute('fill', style.fill || '#475569')
          t.setAttribute('font-family', style.fontFamily || 'sans-serif')
          t.setAttribute('font-size', style.fontSize || '12px')
        }
      })

      const svgData = new XMLSerializer().serializeToString(clonedSvg)
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
      const svgUrl = URL.createObjectURL(svgBlob)

      const image = new Image()
      image.onload = () => {
        try {
          const canvas = document.createElement('canvas')
          canvas.width = width * scale
          canvas.height = height * scale
          const ctx = canvas.getContext('2d')

          // Check if dark theme is active
          const isDark = document.documentElement.dataset.theme === 'dark'
          ctx.fillStyle = isDark ? '#1e293b' : '#ffffff'
          ctx.fillRect(0, 0, canvas.width, canvas.height)

          ctx.scale(scale, scale)
          ctx.drawImage(image, 0, 0, width, height)

          URL.revokeObjectURL(svgUrl)

          canvas.toBlob((pngBlob) => {
            if (!pngBlob) {
              reject(new Error('Failed to create PNG blob.'))
              return
            }
            const pngUrl = URL.createObjectURL(pngBlob)
            const anchor = document.createElement('a')
            anchor.href = pngUrl
            anchor.download = `${filename}.png`
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
            URL.revokeObjectURL(pngUrl)
            resolve()
          }, 'image/png')
        } catch (err) {
          URL.revokeObjectURL(svgUrl)
          reject(err)
        }
      }

      image.onerror = () => {
        URL.revokeObjectURL(svgUrl)
        reject(new Error('Failed to render SVG onto canvas.'))
      }

      image.src = svgUrl
    } catch (err) {
      reject(err)
    }
  })
}
