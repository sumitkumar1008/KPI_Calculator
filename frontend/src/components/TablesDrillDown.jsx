import React, { useEffect, useState } from 'react'
import { calculateDrillDown } from '../utils/drilldownUtils'

function SummaryTableDrillDown({
  title,
  sectionId,
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
  headerStats = null,
}) {
  const [expandedMonths, setExpandedMonths] = useState(new Set())
  const [expandedWeeks, setExpandedWeeks] = useState(new Set())
  const [expandedDailyRows, setExpandedDailyRows] = useState({})

  // Pagination for drill down views
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)

  // Reset inline drill-downs if period or source file changes.
  useEffect(() => {
    setExpandedMonths(new Set())
    setExpandedWeeks(new Set())
    setExpandedDailyRows({})
  }, [period, sourceResponse])

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
    if (period !== 'monthly' || !row.period) return
    setExpandedMonths((previous) => {
      const next = new Set(previous)
      if (next.has(row.period)) next.delete(row.period)
      else next.add(row.period)
      return next
    })
  }

  const toggleWeek = (monthKey, row) => {
    const weekNum = getRowWeekNum(row)
    const weekKey = `${monthKey}:${weekNum}`
    setExpandedWeeks((previous) => {
      const next = new Set(previous)
      if (next.has(weekKey)) next.delete(weekKey)
      else next.add(weekKey)
      return next
    })

    if (!expandedDailyRows[weekKey] && sourceResponse && Array.isArray(sourceResponse.rows)) {
      setExpandedDailyRows((previous) => ({
        ...previous,
        [weekKey]: calculateDrillDown(sourceResponse.rows, tableType, monthKey, weekNum),
      }))
    }
  }

  const resetDrill = () => {
    setExpandedMonths(new Set())
    setExpandedWeeks(new Set())
    setExpandedDailyRows({})
  }

  // Active dataset
  const activeRows = defaultPeriodRows
  const activeLoading = isLoadingDefault
  const activeError = errorDefault

  const totalPages = Math.max(1, Math.ceil(activeRows.length / rowsPerPage))
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = activeRows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  return (
    <section id={sectionId} className="summary-section" aria-label={title}>
      <div className="summary-heading">
        <div>
          <p className="section-label">{subtitle}</p>
          <div className="summary-title-row">
            <h3 className="summary-title-wrap">
              {title}
            </h3>
            {headerStats}
          </div>
        </div>

        <label className="summary-period">
          <span>Time period</span>
          <select
            value={period}
            onChange={(e) => {
              resetDrill()
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
          {`Loading ${period} summary...`}
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
                const canExpandMonth = period === 'monthly'
                const monthKey = row.period
                const monthExpanded = canExpandMonth && expandedMonths.has(monthKey)
                const weekRows = monthExpanded && sourceResponse && Array.isArray(sourceResponse.rows)
                  ? calculateDrillDown(sourceResponse.rows, tableType, monthKey)
                  : []

                return (
                  <React.Fragment key={row.period || idx}>
                    <tr
                      className={canExpandMonth ? `interactive-row ${monthExpanded ? 'expanded-week-row' : ''}` : ''}
                      onClick={canExpandMonth ? () => handleRowClick(row) : undefined}
                      title={canExpandMonth ? (monthExpanded ? 'Click to collapse weekly breakdown' : 'Click to view weekly breakdown') : undefined}
                    >
                      {renderRowWithIndicator(row, canExpandMonth ? 'month' : null, monthExpanded, renderRow)}
                    </tr>

                    {monthExpanded && (
                      <tr className="subtable-row">
                        <td colSpan={columns.length} className="subtable-container-cell">
                          <div className="daily-subtable-wrap">
                            <div className="daily-subtable-title">Weekly Breakdown ({row.period_label || monthKey})</div>
                            {weekRows.length > 0 ? (
                              <table className="daily-subtable">
                                <thead>
                                  <tr>
                                    {columns.map((col) => (
                                      <th key={col.key}>{col.label}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {weekRows.map((weekRow, weekIdx) => {
                                    const weekNum = getRowWeekNum(weekRow)
                                    const weekKey = `${monthKey}:${weekNum}`
                                    const weekExpanded = expandedWeeks.has(weekKey)
                                    const dailyData = expandedDailyRows[weekKey] || []
                                    return (
                                      <React.Fragment key={weekRow.period || weekIdx}>
                                        <tr className="interactive-row" onClick={() => toggleWeek(monthKey, weekRow)} title={weekExpanded ? 'Click to collapse daily breakdown' : 'Click to view daily breakdown'}>
                                          {renderRowWithIndicator(weekRow, 'week', weekExpanded, renderRow)}
                                        </tr>
                                        {weekExpanded && dailyData.map((dailyRow, dayIdx) => (
                                          <tr key={dailyRow.period || dayIdx}>
                                            {renderRow(dailyRow)}
                                          </tr>
                                        ))}
                                      </React.Fragment>
                                    )
                                  })}
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
function renderRowWithIndicator(row, rowLevel, isExpanded, renderRow) {
  const defaultRowContent = renderRow(row)
  if (!rowLevel) return defaultRowContent

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
