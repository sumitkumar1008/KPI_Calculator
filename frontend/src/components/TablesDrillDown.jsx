import { useEffect, useRef, useState } from 'react'
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
  const [drillLevel, setDrillLevel] = useState(0) // 0: default (monthly/global), 1: 4 weeks, 2: 7 days daily
  const [selectedMonth, setSelectedMonth] = useState(null)
  const [selectedMonthLabel, setSelectedMonthLabel] = useState(null)
  const [selectedWeek, setSelectedWeek] = useState(null)
  const [selectedWeekLabel, setSelectedWeekLabel] = useState(null)

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
    setSelectedWeek(null)
    setSelectedWeekLabel(null)
    setDrillRows([])
  }, [period, sourceResponse])

  // Calculate level 1 or level 2 drill-down data instantly from memory
  useEffect(() => {
    if (drillLevel === 0 || !sourceResponse || !selectedMonth) return

    const cacheKey = `${tableType}_${selectedMonth}_${drillLevel === 2 ? selectedWeek : 'weeks'}`
    
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
        drillLevel === 2 ? selectedWeek : null
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
    if (drillLevel === 2 && selectedWeek !== null) {
      endpoint.searchParams.set('week', selectedWeek)
    }

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
  }, [drillLevel, selectedMonth, selectedWeek, tableType, sourceResponse])

  const handleRowClick = (row) => {
    if (drillLevel === 0) {
      // Month -> Weeks
      const monthKey = row.period_label || row.period
      setSelectedMonth(monthKey)
      setSelectedMonthLabel(row.period_label || row.period)
      setDrillLevel(1)
    } else if (drillLevel === 1) {
      // Week -> 7 Days Daily
      let weekNum = 1
      if (typeof row.period === 'string' && row.period.includes('-W')) {
        const parts = row.period.split('-W')
        weekNum = parseInt(parts[parts.length - 1], 10) || 1
      } else if (row.period_label && row.period_label.toLowerCase().includes('week')) {
        const match = row.period_label.match(/week\s*(\d+)/i)
        if (match) weekNum = parseInt(match[1], 10)
      }
      setSelectedWeek(weekNum)
      setSelectedWeekLabel(row.period_label || `Week ${weekNum}`)
      setDrillLevel(2)
    }
  }

  const goBackLevel = () => {
    if (drillLevel === 2) {
      setDrillLevel(1)
      setSelectedWeek(null)
      setSelectedWeekLabel(null)
    } else if (drillLevel === 1) {
      setDrillLevel(0)
      setSelectedMonth(null)
      setSelectedMonthLabel(null)
    }
  }

  const resetDrill = () => {
    setDrillLevel(0)
    setSelectedMonth(null)
    setSelectedMonthLabel(null)
    setSelectedWeek(null)
    setSelectedWeekLabel(null)
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
              <button
                type="button"
                className={`breadcrumb-btn ${drillLevel === 1 ? 'is-active' : ''}`}
                onClick={() => {
                  setDrillLevel(1)
                  setSelectedWeek(null)
                }}
              >
                {selectedMonthLabel}
              </button>
              {drillLevel === 2 && (
                <>
                  <span className="breadcrumb-separator">/</span>
                  <span className="breadcrumb-btn is-active">{selectedWeekLabel}</span>
                </>
              )}

              <button type="button" className="drill-back-btn" onClick={goBackLevel}>
                ← Back
              </button>
            </div>
          )}
        </div>

        <label className="summary-period">
          <span>Time period</span>
          <select
            value={drillLevel === 0 ? period : drillLevel === 1 ? 'weekly' : 'daily'}
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
            : drillLevel === 1
            ? `Loading weekly drill-down for ${selectedMonthLabel}...`
            : `Loading daily drill-down for ${selectedWeekLabel}...`}
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
              {visibleRows.map((row, idx) => (
                <tr
                  key={row.period || idx}
                  className={drillLevel < 2 ? 'interactive-row' : ''}
                  onClick={() => drillLevel < 2 && handleRowClick(row)}
                >
                  {renderRow(row)}
                </tr>
              ))}
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

export default SummaryTableDrillDown
