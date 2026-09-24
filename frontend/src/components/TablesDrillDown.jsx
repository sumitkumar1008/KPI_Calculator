import React, { useEffect, useState } from 'react'
import { calculateDrillDown } from '../utils/drilldownUtils'
import DownloadDropdown from './DownloadDropdown'
import { exportDataViaApi } from '../utils/exportUtils'

// Helper to safely extract row array from any drill-down result format
function extractDrillRows(drillResult) {
  if (Array.isArray(drillResult)) return drillResult
  if (Array.isArray(drillResult?.summary)) return drillResult.summary
  if (Array.isArray(drillResult?.rows)) return drillResult.rows
  if (Array.isArray(drillResult?.data)) return drillResult.data
  return []
}

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

  // Handle main table row clicks:
  // In monthly mode -> toggle month's weekly breakdown
  // In weekly mode -> toggle week's daily breakdown directly
  const handleMainRowClick = (row) => {
    if (!row.period) return
    if (period === 'monthly') {
      setExpandedMonths((previous) => {
        const next = new Set(previous)
        if (next.has(row.period)) next.delete(row.period)
        else next.add(row.period)
        return next
      })
    } else if (period === 'weekly') {
      const weekNum = getRowWeekNum(row)
      let cleanMonth = row.period
      if (typeof cleanMonth === 'string' && cleanMonth.includes('-W')) {
        cleanMonth = cleanMonth.split('-W')[0]
      }
      const weekKey = `weekly-mode:${row.period}`
      setExpandedWeeks((previous) => {
        const next = new Set(previous)
        if (next.has(weekKey)) {
          next.delete(weekKey)
        } else {
          next.add(weekKey)
          if (!expandedDailyRows[weekKey] && sourceResponse?.rows) {
            const drill = calculateDrillDown(sourceResponse.rows, tableType, cleanMonth, weekNum)
            const dailyRows = extractDrillRows(drill)
            setExpandedDailyRows((prev) => ({
              ...prev,
              [weekKey]: dailyRows,
            }))
          }
        }
        return next
      })
    }
  }

  // Toggle week when inside a monthly subtable
  const toggleWeek = (monthKey, row) => {
    const weekNum = getRowWeekNum(row)
    let cleanMonth = monthKey
    if (typeof cleanMonth === 'string' && cleanMonth.includes('-W')) {
      cleanMonth = cleanMonth.split('-W')[0]
    }
    const weekKey = `${cleanMonth}:${weekNum}`
    setExpandedWeeks((previous) => {
      const next = new Set(previous)
      if (next.has(weekKey)) {
        next.delete(weekKey)
      } else {
        next.add(weekKey)
        if (!expandedDailyRows[weekKey] && sourceResponse?.rows) {
          const rawRows = sourceResponse.rows
          const drill = calculateDrillDown(rawRows, tableType, cleanMonth, weekNum)
          const dailyRows = extractDrillRows(drill)
          setExpandedDailyRows((prev) => ({
            ...prev,
            [weekKey]: dailyRows,
          }))
        }
      }
      return next
    })
  }

  const resetDrill = () => {
    setExpandedMonths(new Set())
    setExpandedWeeks(new Set())
    setExpandedDailyRows({})
    setCurrentPage(1)
  }

  // Active dataset
  const activeRows = defaultPeriodRows
  const activeLoading = isLoadingDefault
  const activeError = errorDefault

  const totalPages = Math.max(1, Math.ceil(activeRows.length / rowsPerPage))
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = activeRows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  const handleExport = (format) => {
    if (!activeRows || activeRows.length === 0) return

    const exportCols = columns.map((c) => ({
      key: c.key,
      label: c.label || c.key,
    }))

    const exportData = activeRows.map((row) => {
      const item = {}
      columns.forEach((col) => {
        if (col.key === 'period') {
          item[col.key] = row.period_label || row.period || '—'
        } else {
          const val = row[col.key] !== undefined ? row[col.key] : row[`AVG_${col.key}`]
          item[col.key] = val !== undefined && val !== null ? val : '—'
        }
      })
      return item
    })

    const safeTitle = `${title} (${period.toUpperCase()})`
    const safeFilename = `${(sectionId || title || 'kpi_summary').toLowerCase().replace(/[^a-z0-9]+/g, '_')}_${period}`

    return exportDataViaApi({
      format,
      filename: safeFilename,
      title: safeTitle,
      sheetName: title.slice(0, 30),
      columns: exportCols,
      data: exportData,
    })
  }

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

        <div className="summary-controls" style={{ display: 'flex', alignItems: 'flex-end', gap: '12px' }}>
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

          <DownloadDropdown
            onDownloadExcel={() => handleExport('xlsx')}
            onDownloadCsv={() => handleExport('csv')}
            disabled={activeLoading || activeRows.length === 0}
            tooltip={`Export ${title} data`}
          />
        </div>
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
                const isMonthly = period === 'monthly'
                const isWeekly = period === 'weekly'
                const monthKey = row.period
                const monthExpanded = isMonthly && expandedMonths.has(monthKey)

                // Weekly direct drilldown state
                const weekNum = isWeekly ? getRowWeekNum(row) : null
                const weekKeyDirect = isWeekly ? `weekly-mode:${row.period}` : null
                const weekExpandedDirect = isWeekly && expandedWeeks.has(weekKeyDirect)
                const directDailyData = isWeekly && weekExpandedDirect
                  ? (expandedDailyRows[weekKeyDirect] || (
                      sourceResponse?.rows
                        ? extractDrillRows(calculateDrillDown(sourceResponse.rows, tableType, row.period.split('-W')[0], weekNum))
                        : []
                    ))
                  : []

                // Weekly breakdown rows when month is expanded
                const weekRows = monthExpanded && sourceResponse && Array.isArray(sourceResponse.rows)
                  ? extractDrillRows(calculateDrillDown(sourceResponse.rows, tableType, monthKey))
                  : []

                const isInteractive = isMonthly || isWeekly
                const isExpanded = isMonthly ? monthExpanded : (isWeekly ? weekExpandedDirect : false)

                return (
                  <React.Fragment key={row.period || idx}>
                    <tr
                      className={isInteractive ? `interactive-row ${isExpanded ? 'expanded-week-row' : ''}` : ''}
                      onClick={isInteractive ? () => handleMainRowClick(row) : undefined}
                      title={
                        isMonthly
                          ? (monthExpanded ? 'Click to collapse weekly breakdown' : 'Click to view weekly breakdown')
                          : isWeekly
                          ? (weekExpandedDirect ? 'Click to collapse daily breakdown' : 'Click to view daily breakdown')
                          : undefined
                      }
                    >
                      {renderRowWithIndicator(
                        row,
                        isMonthly ? 'month' : (isWeekly ? 'week' : null),
                        isExpanded,
                        renderRow
                      )}
                    </tr>

                    {/* Level 1: Month expanded -> shows weekly breakdown subtable */}
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
                                    const wNum = getRowWeekNum(weekRow)
                                    let cleanM = monthKey
                                    if (typeof cleanM === 'string' && cleanM.includes('-W')) {
                                      cleanM = cleanM.split('-W')[0]
                                    }
                                    const wKey = `${cleanM}:${wNum}`
                                    const wExpanded = expandedWeeks.has(wKey)
                                    const dailyData = expandedDailyRows[wKey] || (
                                      sourceResponse?.rows
                                        ? extractDrillRows(calculateDrillDown(sourceResponse.rows, tableType, cleanM, wNum))
                                        : []
                                    )
                                    return (
                                      <React.Fragment key={weekRow.period || weekIdx}>
                                        <tr
                                          className="interactive-row"
                                          onClick={() => toggleWeek(monthKey, weekRow)}
                                          title={wExpanded ? 'Click to collapse daily breakdown' : 'Click to view daily breakdown'}
                                        >
                                          {renderRowWithIndicator(weekRow, 'week', wExpanded, renderRow)}
                                        </tr>
                                        {/* Level 2: Week expanded -> shows daily rows */}
                                        {wExpanded && (
                                          dailyData.length > 0 ? (
                                            dailyData.map((dailyRow, dayIdx) => (
                                              <tr key={dailyRow.period || dayIdx} className="daily-data-row">
                                                {renderRowWithIndicator(dailyRow, 'day', false, renderRow)}
                                              </tr>
                                            ))
                                          ) : (
                                            <tr className="empty-subtable-row">
                                              <td colSpan={columns.length} style={{ padding: '8px 18px', color: 'var(--muted)', fontStyle: 'italic', fontSize: '11px' }}>
                                                No daily records found for this week.
                                              </td>
                                            </tr>
                                          )
                                        )}
                                      </React.Fragment>
                                    )
                                  })}
                                </tbody>
                              </table>
                            ) : (
                              <p className="empty-results" style={{ padding: '10px 14px', margin: 0 }}>
                                No weekly records found for this month.
                              </p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}

                    {/* Direct Weekly drilldown -> shows daily breakdown subtable */}
                    {isWeekly && weekExpandedDirect && (
                      <tr className="subtable-row">
                        <td colSpan={columns.length} className="subtable-container-cell">
                          <div className="daily-subtable-wrap">
                            <div className="daily-subtable-title">Daily Breakdown ({row.period_label || row.period})</div>
                            {directDailyData.length > 0 ? (
                              <table className="daily-subtable">
                                <thead>
                                  <tr>
                                    {columns.map((col) => (
                                      <th key={col.key}>{col.label}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {directDailyData.map((dailyRow, dayIdx) => (
                                    <tr key={dailyRow.period || dayIdx} className="daily-data-row">
                                      {renderRowWithIndicator(dailyRow, 'day', false, renderRow)}
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

// Helper to render row with a subtle expand/collapse indicator (▼/▶) or day bullet (•)
function renderRowWithIndicator(row, rowLevel, isExpanded, renderRow) {
  const defaultRowContent = renderRow(row)
  if (!rowLevel) return defaultRowContent

  const children = React.Children.toArray(defaultRowContent.props.children)
  if (children.length === 0) return defaultRowContent

  const firstCell = children[0]
  const isDay = rowLevel === 'day'
  const modifiedFirstCell = (
    <td
      key={firstCell.key || 'first-cell'}
      style={isDay ? { paddingLeft: '32px' } : undefined}
    >
      {!isDay ? (
        <span className="week-expand-indicator" style={{ display: 'inline-block', width: '16px', userSelect: 'none' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      ) : (
        <span className="day-bullet-indicator" style={{ display: 'inline-block', width: '16px', color: 'var(--accent)', opacity: 0.7, userSelect: 'none' }}>
          •
        </span>
      )}
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
