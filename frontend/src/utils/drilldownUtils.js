/**
 * Client-Side Instant Drill-Down & Aggregation Utilities
 * ========================================================
 * Pre-computes and aggregates periods (daily, weekly, monthly)
 * and drill-downs (month -> 4 weeks -> 7 days daily) directly in memory
 * for zero-latency instant responses.
 */

// Helper to format duration seconds as cumulative HH:MM:SS (e.g. 20:35:59)
export function formatSecondsToHHMMSS(totalSec) {
  if (totalSec === null || totalSec === undefined || isNaN(totalSec) || totalSec < 0) {
    return '—'
  }
  const rounded = Math.round(totalSec)
  const hours = Math.floor(rounded / 3600)
  const remSec = rounded % 3600
  const minutes = Math.floor(remSec / 60)
  const seconds = remSec % 60

  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
}

// Parse string duration (HH:MM:SS or Xd HH:MM:SS) to seconds
export function parseDurationToSeconds(val) {
  if (!val && val !== 0) return null
  if (typeof val === 'number') return val >= 0 ? val : null
  const str = String(val).trim()
  if (['none', 'null', '', 'n/a', 'nan', '—', '-'].includes(str.toLowerCase())) return null

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

// Helper to extract creation date from various property names
export function getRowCreationTime(row) {
  if (!row) return null
  return (
    row.SRCREATIONTIME ||
    row.CREATIONTIME ||
    row.creation_time ||
    row.CreationTime ||
    row.SR_CREATION_TIME ||
    row.srcreationtime ||
    null
  )
}

// Parse creation date into Date object
export function parseSRDate(val) {
  if (!val) return null
  if (val instanceof Date) return isNaN(val.getTime()) ? null : val
  if (typeof val === 'number') {
    if (val > 30000 && val < 70000) {
      return new Date(Math.round((val - 25569) * 86400 * 1000))
    }
    const d = new Date(val)
    return isNaN(d.getTime()) ? null : d
  }

  const value = String(val).trim()
  if (!value || ['nan', 'none', 'null', '', 'nat'].includes(value.toLowerCase())) {
    return null
  }

  // ISO / Hyphenated: 2026-08-21 or 2026-08-21T08:00:00 or 2026-08-21 08:00:00
  const isoMatch = value.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?$/)
  if (isoMatch) {
    const [, year, month, day, hour = '0', minute = '0', second = '0'] = isoMatch
    const d = new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second))
    return isNaN(d.getTime()) ? null : d
  }

  // Day/Month/Year or Month/Day/Year: 21/08/2026 or 08/21/2026
  const separatedDateMatch = value.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/)
  if (separatedDateMatch) {
    const [, firstPart, secondPart, year, hour = '0', minute = '0', second = '0'] = separatedDateMatch
    const firstNumber = Number(firstPart)
    const secondNumber = Number(secondPart)
    const isClearDayFirst = firstNumber > 12 && secondNumber <= 12
    const month = isClearDayFirst ? secondNumber : firstNumber
    const day = isClearDayFirst ? firstNumber : secondNumber
    const d = new Date(Number(year), month - 1, day, Number(hour), Number(minute), Number(second))
    return isNaN(d.getTime()) ? null : d
  }

  const dt = new Date(value)
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
    const dt = parseSRDate(getRowCreationTime(row))
    if (!dt) return

    const year = dt.getFullYear()
    const month = String(dt.getMonth() + 1).padStart(2, '0')
    const day = String(dt.getDate()).padStart(2, '0')
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ]
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
      const nCount = bucketRows.length - yCount
      return {
        period: key,
        period_label: buckets[key].period_label,
        Y_count: yCount,
        N_count: nCount,
        Y_percentage: bucketRows.length ? Number(((yCount / bucketRows.length) * 100).toFixed(2)) : 0,
        N_percentage: bucketRows.length ? Number(((nCount / bucketRows.length) * 100).toFixed(2)) : 0,
        total_count: bucketRows.length,
      }
    } else if (tableType === 'automation_rca') {
      const yesValues = new Set(['1', 'true', 't', 'y', 'yes', 'on'])
      const yCount = bucketRows.filter((r) =>
        yesValues.has(String(r.AUTOMATION_RCA_CONCLUSION || '').trim().toLowerCase())
      ).length
      const nCount = bucketRows.length - yCount
      return {
        period: key,
        period_label: buckets[key].period_label,
        Y_count: yCount,
        N_count: nCount,
        Y_percentage: bucketRows.length ? Number(((yCount / bucketRows.length) * 100).toFixed(2)) : 0,
        N_percentage: bucketRows.length ? Number(((nCount / bucketRows.length) * 100).toFixed(2)) : 0,
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
            const rawVal = r[kpi] !== undefined ? r[kpi] : r[`AVG_${kpi}`]
            const parsed = parseDurationToSeconds(rawVal)
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

  let cleanMonth = String(monthStr).trim()
  if (cleanMonth.includes('-W')) {
    cleanMonth = cleanMonth.split('-W')[0]
  } else if (cleanMonth.toLowerCase().includes(' - week')) {
    cleanMonth = cleanMonth.split(/ - week/i)[0]
  }
  const normMonth = cleanMonth.trim().toLowerCase()

  // Filter rows by month
  const monthRows = rows.filter((r) => {
    const dt = parseSRDate(getRowCreationTime(r))
    if (!dt) return false
    const year = dt.getFullYear()
    const month = String(dt.getMonth() + 1).padStart(2, '0')
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ]
    const fullMonth = `${monthNames[dt.getMonth()]} ${year}`.toLowerCase()
    const monthKey = `${year}-${month}`.toLowerCase()
    return monthKey === normMonth || fullMonth === normMonth
  })

  if (weekNum !== null && weekNum !== undefined && String(weekNum).trim() !== '') {
    // Level 2: Week -> 7 Days Daily breakdown
    const targetWeek = Number(weekNum)
    const weekRows = monthRows.filter((r) => {
      const dt = parseSRDate(getRowCreationTime(r))
      return dt && getWeekNum(dt) === targetWeek
    })
    return calculatePeriodSummary(weekRows, 'daily', tableType)
  } else {
    // Level 1: Month -> 4 Weeks breakdown
    return calculatePeriodSummary(monthRows, 'weekly', tableType)
  }
}
