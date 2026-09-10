import React, { useEffect, useRef, useState } from 'react'
import { calculateDrillDown } from '../utils/drilldownUtils'

function SummaryTableDrillDown({
  title,
  subtitle,
  tableType = 'avg',
  sourceResponse,
  columns,
  renderRow,
  defaultPeriodRows = [],
  isLoadingDefault = false,
  errorDefault = null,
  period = 'monthly',
  onPeriodChange = () => {},
}) {
  const [drillLevel, setDrillLevel] = useState(0) // 0: default (monthly), 1: 4 weeks view
  const [selectedMonth, setSelectedMonth] = useState(null)
  const [selectedMonthLabel, setSelectedMonthLabel] = useState(null)

  // Track expanded week numbers in Level 1 view (e.g. Set containing week 1, 2, etc.)
  const [expandedWeeks, setExpandedWeeks] = useState(new Set())
  const [expandedDailyRows, setExpandedDailyRows] = useState({})

  const [drillRows, setDrillRows] = useState([])
  const [isDrillLoading, setIsDrillLoading] = useState(false)
  const [drillError, setDrillError] = useState(null)

  // In-memory cache for drilldown responses
  const drillCacheRef = useRef({})

  // Reset drill cache when file changes
  useEffect(() => {
    drillCacheRef.current = {}
  }, [sourceResponse])

  // Pagination for drill down views
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)

  // Reset drill-down if period or source file changes
  useEffect(() => {
    setDrillLevel(0)
    setSelectedMonth(null)
    setSelectedMonthLabel(null)
    setExpandedWeeks(new Set())
    setExpandedDailyRows({})
    setDrillRows([])
  }, [period, sourceResponse])

  // Calculate Level 1 (Month -> 4 Weeks) drill-down data instantly from memory
  useEffect(() => {
    if (drillLevel === 0 || !sourceResponse || !selectedMonth) return

    const cacheKey = `${tableType}_${selectedMonth}_weeks`
    
    // Check drill cache
    if (drillCacheRef.current[cacheKey]) {
      setDrillRows(drillCacheRef.current[cacheKey])
      setIsDrillLoading(false)
      setDrillError(null)
      setCurrentPage(1)
      return
    }

    // Instant in-memory calculation from uploaded row records
    if (Array.isArray(sourceResponse.rows)) {
      const summary = calculateDrillDown(
        sourceResponse.rows,
        tableType,
        selectedMonth,
        null
      )
      drillCacheRef.current[cacheKey] = summary
      setDrillRows(summary)
      setIsDrillLoading(false)
      setDrillError(null)
      setCurrentPage(1)
      return
    }

    // Fallback network fetch if rows array is absent
    const controller = new AbortController()
    const endpoint = new URL(
      import.meta.env.VITE_DRILLDOWN_API_ENDPOINT || '/api/v1/kpi/drilldown',
      window.location.origin,
    )
    endpoint.searchParams.set('table_type', tableType)
    endpoint.searchParams.set('month', selectedMonth)

    setIsDrillLoading(true)
    setDrillError(null)

    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourceResponse),
      signal: controller.signal,
    })
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data?.error || `Server error HTTP ${res.status}.`)
        return data
      })
      .then((data) => {
        const summary = Array.isArray(data.summary) ? data.summary : []
        drillCacheRef.current[cacheKey] = summary
        setDrillRows(summary)
        setCurrentPage(1)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setDrillRows([])
          setDrillError(err.message || 'Drill down data could not be loaded.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsDrillLoading(false)
      })

    return () => controller.abort()
  }, [drillLevel, selectedMonth, tableType, sourceResponse])

  // Extract week number from row (e.g. "Week 1", "2026-08-W1")
  const getRowWeekNum = (row) => {
    let weekNum = 1
    if (typeof row.period === 'string' && row.period.includes('-W')) {
      const parts = row.period.split('-W')
      weekNum = parseInt(parts[parts.length - 1], 10) || 1
    } else if (row.period_label && row.period_label.toLowerCase().includes('week')) {
      const match = row.period_label.match(/week\s*(\d+)/i)
      if (match) weekNum = parseInt(match[1], 10)
    }
    return weekNum
  }

  const handleRowClick = (row) => {
    if (drillLevel === 0) {
      // Month -> 4 Weeks
      const monthKey = row.period_label || row.period
      setSelectedMonth(monthKey)
      setSelectedMonthLabel(row.period_label || row.period)
      setExpandedWeeks(new Set())
      setExpandedDailyRows({})
      setDrillLevel(1)
    } else if (drillLevel === 1) {
      // Toggle inline expandable week row (keep rest of weeks visible!)
      const weekNum = getRowWeekNum(row)
      
      setExpandedWeeks((prev) => {
        const next = new Set(prev)
        if (next.has(weekNum)) {
          next.delete(weekNum)
        } else {
          next.add(weekNum)

          // Compute 7 daily rows for this week if not already computed
          if (!expandedDailyRows[weekNum] && sourceResponse && Array.isArray(sourceResponse.rows)) {
            const dailySummary = calculateDrillDown(sourceResponse.rows, tableType, selectedMonth, weekNum)
            setExpandedDailyRows((prevDaily) => ({
              ...prevDaily,
              [weekNum]: dailySummary,
            }))
          }
        }
        return next
      })
    }
  }

  const resetDrill = () => {
    setDrillLevel(0)
    setSelectedMonth(null)
    setSelectedMonthLabel(null)
    setExpandedWeeks(new Set())
    setExpandedDailyRows({})
  }

  // Active dataset
  const activeRows = drillLevel === 0 ? defaultPeriodRows : drillRows
  const activeLoading = drillLevel === 0 ? isLoadingDefault : isDrillLoading
  const activeError = drillLevel === 0 ? errorDefault : drillError

  const totalPages = Math.max(1, Math.ceil(activeRows.length / rowsPerPage))
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = activeRows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  return (
    <section className="summary-section" aria-label={title}>
      <div className="summary-heading">
        <div>
          <p className="section-label">{subtitle}</p>
          <h3 className="summary-title-wrap">
            {title}
          </h3>

          {/* Breadcrumbs Navigation */}
          {drillLevel > 0 && (
            <div className="drill-breadcrumbs">
              <button type="button" className="breadcrumb-btn" onClick={resetDrill}>
                Monthly Overview
              </button>
              <span className="breadcrumb-separator">/</span>
              <span className="breadcrumb-btn is-active">{selectedMonthLabel}</span>

              <button type="button" className="drill-back-btn" onClick={resetDrill}>
                ← Back
              </button>
            </div>
          )}
        </div>

        <label className="summary-period">
          <span>Time period</span>
          <select
            value={drillLevel === 0 ? period : 'weekly'}
            onChange={(e) => {
              setDrillLevel(0)
              onPeriodChange(e.target.value)
            }}
            disabled={activeLoading}
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      </div>

      {activeError && (
        <p className="message message--error summary-message" role="alert">
          <span aria-hidden="true">!</span>
          {activeError}
        </p>
      )}

      {activeLoading ? (
        <p className="empty-results">
          {drillLevel === 0
            ? `Loading ${period} summary...`
            : `Loading weekly breakdown for ${selectedMonthLabel}...`}
        </p>
      ) : activeRows.length > 0 ? (
        <div className="results-table-wrap">
          <table className="results-table summary-table drillable-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col.key} scope="col">
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row, idx) => {
                const weekNum = drillLevel === 1 ? getRowWeekNum(row) : null
                const isExpanded = drillLevel === 1 && expandedWeeks.has(weekNum)
                const dailyData = isExpanded ? (expandedDailyRows[weekNum] || []) : []

                return (
                  <React.Fragment key={row.period || idx}>
                    <tr
                      className={`interactive-row ${isExpanded ? 'expanded-week-row' : ''}`}
                      onClick={() => handleRowClick(row)}
                      title={
                        drillLevel === 0
                          ? 'Click to view 4 weeks'
                          : isExpanded
                          ? 'Click to collapse 7-day daily breakdown'
                          : 'Click to expand 7-day daily breakdown'
                      }
                    >
                      {renderRowWithIndicator(row, drillLevel, isExpanded, renderRow)}
                    </tr>

                    {/* Inline Expandable Daily Breakdown Sub-Table (Keep rest of weeks visible!) */}
                    {isExpanded && (
                      <tr className="subtable-row">
                        <td colSpan={columns.length} className="subtable-container-cell">
                          <div className="daily-subtable-wrap">
                            <div className="daily-subtable-title">
                              7-Day Daily Breakdown ({row.period_label || `Week ${weekNum}`})
                            </div>
                            {dailyData.length > 0 ? (
                              <table className="daily-subtable">
                                <thead>
                                  <tr>
                                    {columns.map((col) => (
                                      <th key={col.key}>{col.label}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {dailyData.map((dailyRow, dIdx) => (
                                    <tr key={dailyRow.period || dIdx}>
                                      {renderRow(dailyRow)}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            ) : (
                              <p className="empty-results" style={{ padding: '10px 14px', margin: 0 }}>
                                No daily records found for this week.
                              </p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-results">No summary data available for this view.</p>
      )}

      {activeRows.length > 0 && (
        <div className="pagination-controls" aria-label="Table pagination">
          <label className="rows-per-page">
            Rows per page
            <select value={rowsPerPage} onChange={(e) => setRowsPerPage(Number(e.target.value))}>
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>
          <span className="pagination-status">
            Showing {pageStartIndex + 1}-{Math.min(pageStartIndex + rowsPerPage, activeRows.length)} of{' '}
            {activeRows.length}
          </span>
          <div className="pagination-buttons">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => p - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => p + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// Helper to render row with a subtle expand/collapse indicator (▼/▶) for Level 1 weekly rows
function renderRowWithIndicator(row, drillLevel, isExpanded, renderRow) {
  const defaultRowContent = renderRow(row)
  if (drillLevel !== 1) return defaultRowContent

  // Wrap the first cell with expand/collapse arrow
  const children = React.Children.toArray(defaultRowContent.props.children)
  if (children.length === 0) return defaultRowContent

  const firstCell = children[0]
  const modifiedFirstCell = (
    <td key={firstCell.key || 'first-cell'}>
      <span className="week-expand-indicator">{isExpanded ? '▼' : '▶'}</span>
      {firstCell.props.children}
    </td>
  )

  return (
    <>
      {modifiedFirstCell}
      {children.slice(1)}
    </>
  )
}

export default SummaryTableDrillDown
