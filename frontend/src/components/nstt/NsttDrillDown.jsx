import React, { useState, useMemo, useEffect } from 'react'
import { useNstt } from '../../context/NsttContext'
import './NsttDrillDown.css'

export default function NsttDrillDown() {
  const {
    isDrilldownOpen,
    isDrilldownLoading,
    drilldownCategory,
    drilldownData,
    closeDrilldown,
  } = useNstt()

  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Reset pagination on category change
  useEffect(() => {
    setCurrentPage(1)
    setSearchTerm('')
  }, [drilldownCategory])

  // ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isDrilldownOpen) {
        closeDrilldown()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isDrilldownOpen, closeDrilldown])

  const records = useMemo(() => {
    return Array.isArray(drilldownData?.records) ? drilldownData.records : []
  }, [drilldownData])

  // Only display AUTOMATION_IMPACT for the 5 Different NSTT categories
  const isDifferentNsttCategory = useMemo(() => {
    const cat = String(drilldownCategory || '').toLowerCase()
    if (cat.includes('different_nstt') || cat.includes('diff_nstt')) return true
    if (records.length > 0 && records.every((r) => Boolean(r.diff_nstt_category))) return true
    return false
  }, [drilldownCategory, records])

  // Detect if current drilldown is part of the Manual Captured section
  const isManualCaptured = useMemo(() => {
    const cat = String(drilldownCategory || '').toLowerCase()
    if (cat === 'manual' || cat.startsWith('manual.') || cat.includes('engineer')) {
      return true
    }
    if (records.length > 0 && records.every((r) => r.capture_type === 'Manual')) {
      return true
    }
    return false
  }, [drilldownCategory, records])

  // Search filter across key fields
  const filteredRecords = useMemo(() => {
    if (!searchTerm.trim()) return records
    const term = searchTerm.toLowerCase()
    return records.filter((rec) => {
      const srNum = String(rec.SRNUMBER || rec.SR_NUMBER || rec['SR NUMBER'] || rec.SRNO || rec['SR NO'] || '')
      return (
        srNum.toLowerCase().includes(term) ||
        String(rec.INCIDENTID || '').toLowerCase().includes(term) ||
        (!isManualCaptured && String(rec.AUTOMATION_UPDATE_NSTT_NUMBER || '').toLowerCase().includes(term)) ||
        String(rec.ATTRIBUTEDTO || '').toLowerCase().includes(term) ||
        String(rec.FACTORY || '').toLowerCase().includes(term) ||
        String(rec.DESCRIPTION || '').toLowerCase().includes(term) ||
        String(rec.AUTOMATION_RCA_CONCLUSION_TEXT || '').toLowerCase().includes(term) ||
        String(rec.INCIDENT_IMPACT || '').toLowerCase().includes(term) ||
        (isDifferentNsttCategory && String(rec.AUTOMATION_IMPACT || '').toLowerCase().includes(term))
      )
    })
  }, [records, searchTerm, isDifferentNsttCategory, isManualCaptured])

  // Pagination slice
  const totalRecords = filteredRecords.length
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize))
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredRecords.slice(start, start + pageSize)
  }, [filteredRecords, currentPage, pageSize])

  if (!isDrilldownOpen) return null

  // Format category title nicely
  const formatCategoryTitle = (cat) => {
    if (!cat) return 'Record Drilldown'
    return cat
      .split('.')
      .map((part) => part.replace(/_/g, ' ').toUpperCase())
      .join(' ➔ ')
  }

  const exportToCsv = () => {
    if (!filteredRecords.length) return
    const excludedCols = new Set([
      'capture_type',
      'nstt_type',
      'CAPTURE_TYPE',
      'NSTT_TYPE',
      'is_total_sr',
      'is_nstt',
    ])
    if (!isDifferentNsttCategory) {
      excludedCols.add('AUTOMATION_IMPACT')
      excludedCols.add('automation_impact')
    }
    if (isManualCaptured) {
      excludedCols.add('AUTOMATION_UPDATE_NSTT_NUMBER')
      excludedCols.add('automation_update_nstt_number')
    }
    const headers = Object.keys(filteredRecords[0]).filter((h) => !excludedCols.has(h))
    const csvRows = [
      headers.join(','),
      ...filteredRecords.map((r) =>
        headers.map((h) => `"${String(r[h] ?? '').replace(/"/g, '""')}"`).join(',')
      ),
    ]
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `NSTT_Drilldown_${drilldownCategory || 'export'}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="drilldown-backdrop" onClick={closeDrilldown} role="dialog" aria-modal="true">
      <div className="drilldown-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drilldown-header">
          <div className="drilldown-header-title">
            <span className="drilldown-badge">Drill-down Records</span>
            <h2>{formatCategoryTitle(drilldownCategory)}</h2>
            <p className="drilldown-meta">
              Showing <strong>{totalRecords.toLocaleString()}</strong> record{totalRecords === 1 ? '' : 's'}
              {searchTerm && ` (filtered from ${records.length.toLocaleString()})`}
            </p>
          </div>

          <div className="drilldown-header-actions">
            {records.length > 0 && (
              <button type="button" className="btn-drill-export" onClick={exportToCsv}>
                ⬇ Export CSV
              </button>
            )}
            <button
              type="button"
              className="btn-drill-close"
              onClick={closeDrilldown}
              aria-label="Close drawer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Search & Controls */}
        <div className="drilldown-controls">
          <div className="drill-search-box">
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              type="text"
              placeholder="Search by SR Number, Incident ID, Automation NSTT, Attributed To..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
            />
            {searchTerm && (
              <button
                type="button"
                className="clear-search"
                onClick={() => setSearchTerm('')}
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          <div className="drill-page-size">
            <label htmlFor="drill-page-size-select">Per page:</label>
            <select
              id="drill-page-size-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setCurrentPage(1)
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        {/* Content Table */}
        <div className="drilldown-body">
          {isDrilldownLoading ? (
            <div className="drilldown-loading">
              <div className="drilldown-spinner" />
              <p>Fetching records for {drilldownCategory}...</p>
            </div>
          ) : totalRecords === 0 ? (
            <div className="drilldown-empty">
              <span className="empty-icon">📂</span>
              <h3>No matching records</h3>
              <p>{searchTerm ? 'Try adjusting your search query.' : 'No records found in this category.'}</p>
            </div>
          ) : (
            <div className="drilldown-table-wrapper">
              <table className="drilldown-table">
                <thead>
                  <tr>
                    <th className="sticky-col">#</th>
                    <th className="sticky-col-2">INCIDENTID</th>
                    <th>SR NUMBER</th>
                    {!isManualCaptured && <th>AUTOMATION UPDATE NSTT NUMBER</th>}
                    <th>ATTRIBUTEDTO</th>
                    <th>FACTORY</th>
                    <th>AUTO_ALLOCATION</th>
                    <th>INCIDENT_IMPACT</th>
                    {isDifferentNsttCategory && <th>AUTOMATION_IMPACT</th>}
                    <th>SRCREATIONTIME</th>
                    <th>UP_TIME</th>
                    <th>Submit Date</th>
                    <th>DESCRIPTION</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRecords.map((r, i) => {
                    const rowIdx = (currentPage - 1) * pageSize + i + 1

                    // Determine AUTOMATION_IMPACT and INCIDENT_IMPACT
                    let autoImp = r.AUTOMATION_IMPACT
                    let incImp = r.INCIDENT_IMPACT
                    const diffCat = r.diff_nstt_category || ''

                    if (!autoImp && diffCat) {
                      if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both NSA') autoImp = 'NSA'
                      else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both SA') autoImp = 'SA'
                      else if (diffCat === 'Impact Unknown / Not Found in Remedy' || r.nstt_type === 'Different NSTT') autoImp = 'Unknown'
                    }

                    if (!incImp && diffCat) {
                      if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both SA') incImp = 'SA'
                      else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both NSA') incImp = 'NSA'
                      else if (diffCat === 'Impact Unknown / Not Found in Remedy') incImp = 'Unknown'
                    }

                    return (
                      <tr key={r.INCIDENTID || i}>
                        <td className="sticky-col text-muted">{rowIdx}</td>
                        <td className="sticky-col-2 font-mono font-bold">
                          {r.INCIDENTID || '—'}
                        </td>
                        <td className="font-mono">
                          {r.SRNUMBER || r.SR_NUMBER || r['SR NUMBER'] || r.SRNO || r['SR NO'] || '—'}
                        </td>
                        {!isManualCaptured && (
                          <td className="font-mono text-sm" title={r.AUTOMATION_UPDATE_NSTT_NUMBER || ''}>
                            {r.AUTOMATION_UPDATE_NSTT_NUMBER || '—'}
                          </td>
                        )}
                        <td>{r.ATTRIBUTEDTO || '—'}</td>
                        <td>
                          {r.FACTORY ? (
                            <span className={`pill-factory ${r.FACTORY === 'IM' ? 'im' : 'non-im'}`}>
                              {r.FACTORY}
                            </span>
                          ) : '—'}
                        </td>
                        <td>{r.AUTO_ALLOCATION || '—'}</td>
                        <td>
                          {incImp ? (
                            <span className={`pill-impact ${incImp === 'SA' ? 'sa' : (incImp === 'NSA' ? 'nsa' : 'unknown')}`}>
                              {incImp}
                            </span>
                          ) : '—'}
                        </td>
                        {isDifferentNsttCategory && (
                          <td>
                            {autoImp ? (
                              <span className={`pill-impact ${autoImp === 'SA' ? 'sa' : (autoImp === 'NSA' ? 'nsa' : 'unknown')}`}>
                                {autoImp}
                              </span>
                            ) : '—'}
                          </td>
                        )}
                        <td className="font-mono text-sm">{r.SRCREATIONTIME || '—'}</td>
                        <td className="font-mono text-sm">{r.UP_TIME || '—'}</td>
                        <td className="font-mono text-sm">{r['Submit Date'] || '—'}</td>
                        <td className="text-desc" title={r.DESCRIPTION}>
                          {r.DESCRIPTION ? (r.DESCRIPTION.length > 80 ? `${r.DESCRIPTION.slice(0, 80)}...` : r.DESCRIPTION) : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer with Pagination */}
        {totalRecords > 0 && (
          <div className="drilldown-footer">
            <span className="pagination-info">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} records
            </span>
            <div className="pagination-btns">
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(1)}
              >
                « First
              </button>
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                ‹ Prev
              </button>
              <span className="page-indicator">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                Next ›
              </button>
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(totalPages)}
              >
                Last »
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
