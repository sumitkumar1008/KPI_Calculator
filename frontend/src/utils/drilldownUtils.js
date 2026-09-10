/**
 * Client-Side Instant Drill-Down & Aggregation Utilities
 * ========================================================
 * Pre-computes and aggregates periods (daily, weekly, monthly)
 * and drill-downs (month -> 4 weeks -> 7 days daily) directly in memory
 * for zero-latency instant responses.
 */

// Helper to format duration seconds as HH:MM:SS or Xd HH:MM:SS
export function formatSecondsToHHMMSS(totalSec) {
  if (totalSec === null || totalSec === undefined || isNaN(totalSec) || totalSec < 0) {
    return '—'
  }
  const days = Math.floor(totalSec / 86400)
  const remSec = totalSec % 86400
  const hours = Math.floor(remSec / 3600)
  const minutes = Math.floor((remSec % 3600) / 60)
  const seconds = Math.floor(remSec % 60)

  const pad = (n) => String(n).padStart(2, '0')
  const timeStr = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
  return days > 0 ? `${days}d ${timeStr}` : timeStr
}

// Parse string duration (HH:MM:SS or Xd HH:MM:SS) to seconds
export function parseDurationToSeconds(val) {
  if (!val) return null
  if (typeof val === 'number') return val >= 0 ? val : null
  const str = String(val).trim()
  if (['none', 'null', '', 'n/a', 'nan'].includes(str.toLowerCase())) return null

  try {
    let days = 0
    let timePart = str
    if (str.includes('d ')) {
      const parts = str.split('d ')
      days = parseInt(parts[0], 10) || 0
      timePart = parts[1]
    }
    const hms = timePart.split(':').map((p) => parseInt(p, 10))
    if (hms.length === 3 && !hms.some(isNaN)) {
      return days * 86400 + hms[0] * 3600 + hms[1] * 60 + hms[2]
    }
  } catch {
    return null
  }
  return null
}

// Parse creation date into Date object
export function parseSRDate(val) {
  if (!val) return null
  const dt = new Date(val)
  return isNaN(dt.getTime()) ? null : dt
}

// Month-relative week number: Days 1-7 = 1, Days 8-14 = 2, Days 15-21 = 3, Days 22+ = 4
export function getWeekNum(dt) {
  return Math.min(Math.floor((dt.getDate() - 1) / 7) + 1, 4)
}

// Pre-calculate full period summary (daily, weekly, monthly) from rows in memory
export function calculatePeriodSummary(rows, groupBy = 'monthly', tableType = 'avg') {
  if (!Array.isArray(rows) || rows.length === 0) return []

  const buckets = {}

  rows.forEach((row) => {
    const dt = parseSRDate(row.SRCREATIONTIME)
    if (!dt) return

    const year = dt.getFullYear()
    const month = String(dt.getMonth() + 1).padStart(2, '0')
    const day = String(dt.getDate()).padStart(2, '0')
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    const monthName = monthNames[dt.getMonth()]

    let key = ''
    let label = ''

    if (groupBy === 'daily') {
      key = `${year}-${month}-${day}`
      const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      label = `${shortMonths[dt.getMonth()]} ${day}, ${year}`
    } else if (groupBy === 'weekly') {
      const weekNum = getWeekNum(dt)
      key = `${year}-${month}-W${weekNum}`
      label = `${monthName} ${year} - Week ${weekNum}`
    } else {
      // Monthly
      key = `${year}-${month}`
      label = `${monthName} ${year}`
    }

    if (!buckets[key]) {
      buckets[key] = {
        period: key,
        period_label: label,
        rows: [],
      }
    }
    buckets[key].rows.push(row)
  })

  // Sort keys chronologically
  const sortedKeys = Object.keys(buckets).sort()

  return sortedKeys.map((key) => {
    const bucketRows = buckets[key].rows

    if (tableType === 'automation_run') {
      const yCount = bucketRows.filter((r) => String(r.AUTOMATION_RUN || '').toUpperCase() === 'Y').length
      return {
        period: key,
        period_label: buckets[key].period_label,
        Y_count: yCount,
        N_count: bucketRows.length - yCount,
        total_count: bucketRows.length,
      }
    } else if (tableType === 'automation_rca') {
      const yesValues = new Set(['1', 'true', 't', 'y', 'yes', 'on'])
      const yCount = bucketRows.filter((r) => yesValues.has(String(r.AUTOMATION_RCA_CONCLUSION || '').trim().toLowerCase())).length
      return {
        period: key,
        period_label: buckets[key].period_label,
        Y_count: yCount,
        N_count: bucketRows.length - yCount,
        total_count: bucketRows.length,
      }
    } else {
      // KPI Averages (AVG_MTTI, AVG_MTTA, AVG_MTTAck, AVG_MTTR, AVG_MTTr)
      const kpis = ['MTTI', 'MTTA', 'MTTAck', 'MTTR', 'MTTr']
      const summaryRow = {
        period: key,
        period_label: buckets[key].period_label,
        record_count: bucketRows.length,
      }

      kpis.forEach((kpi) => {
        const secKey = `${kpi}_seconds`
        const validSecs = []

        bucketRows.forEach((r) => {
          if (r[secKey] !== undefined && r[secKey] !== null && !isNaN(r[secKey])) {
            validSecs.push(Number(r[secKey]))
          } else {
            const parsed = parseDurationToSeconds(r[kpi])
            if (parsed !== null) validSecs.push(parsed)
          }
        })

        if (validSecs.length > 0) {
          const avgSec = validSecs.reduce((a, b) => a + b, 0) / validSecs.length
          summaryRow[`AVG_${kpi}`] = formatSecondsToHHMMSS(avgSec)
        } else {
          summaryRow[`AVG_${kpi}`] = '—'
        }
      })

      return summaryRow
    }
  })
}

// Calculate drill-down in memory: Month -> 4 Weeks OR Week -> 7 Days Daily
export function calculateDrillDown(rows, tableType, monthStr, weekNum = null) {
  if (!Array.isArray(rows) || rows.length === 0 || !monthStr) return []

  const normMonth = String(monthStr).trim().toLowerCase()

  // Filter rows by month
  const monthRows = rows.filter((r) => {
    const dt = parseSRDate(r.SRCREATIONTIME)
    if (!dt) return false
    const year = dt.getFullYear()
    const month = String(dt.getMonth() + 1).padStart(2, '0')
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    const fullMonth = `${monthNames[dt.getMonth()]} ${year}`.toLowerCase()
    const monthKey = `${year}-${month}`.toLowerCase()
    return monthKey === normMonth || fullMonth === normMonth
  })

  if (weekNum !== null && weekNum !== undefined && String(weekNum).trim() !== '') {
    // Level 2: Week -> 7 Days Daily breakdown
    const targetWeek = Number(weekNum)
    const weekRows = monthRows.filter((r) => {
      const dt = parseSRDate(r.SRCREATIONTIME)
      return dt && getWeekNum(dt) === targetWeek
    })
    return calculatePeriodSummary(weekRows, 'daily', tableType)
  } else {
    // Level 1: Month -> 4 Weeks breakdown
    return calculatePeriodSummary(monthRows, 'weekly', tableType)
  }
}
