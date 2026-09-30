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

  // Search filter across key fields
  const filteredRecords = useMemo(() => {
    if (!searchTerm.trim()) return records
    const term = searchTerm.toLowerCase()
    return records.filter((rec) => {
      return (
        String(rec.INCIDENTID || '').toLowerCase().includes(term) ||
        String(rec.ATTRIBUTEDTO || '').toLowerCase().includes(term) ||
        String(rec.FACTORY || '').toLowerCase().includes(term) ||
        String(rec.DESCRIPTION || '').toLowerCase().includes(term) ||
        String(rec.AUTOMATION_RCA_CONCLUSION_TEXT || '').toLowerCase().includes(term)
      )
    })
  }, [records, searchTerm])

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
    const headers = Object.keys(filteredRecords[0])
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
              placeholder="Search by Incident ID, Attributed To, Factory, Description..."
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
                    <th>ATTRIBUTEDTO</th>
                    <th>FACTORY</th>
                    <th>AUTO_ALLOCATION</th>
                    <th>INCIDENT_IMPACT</th>
                    <th>CAPTURE_TYPE</th>
                    <th>NSTT_TYPE</th>
                    <th>TIMING_TYPE</th>
                    <th>DIFF_CATEGORY</th>
                    <th>EXCEPTION</th>
                    <th>FAILURE_CATEGORY</th>
                    <th>SRCREATIONTIME</th>
                    <th>UP_TIME</th>
                    <th>Submit Date</th>
                    <th>DESCRIPTION</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRecords.map((r, i) => {
                    const rowIdx = (currentPage - 1) * pageSize + i + 1
                    return (
                      <tr key={r.INCIDENTID || i}>
                        <td className="sticky-col text-muted">{rowIdx}</td>
                        <td className="sticky-col-2 font-mono font-bold">
                          {r.INCIDENTID || '—'}
                        </td>
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
                          {r.INCIDENT_IMPACT ? (
                            <span className={`pill-impact ${r.INCIDENT_IMPACT === 'SA' ? 'sa' : 'nsa'}`}>
                              {r.INCIDENT_IMPACT}
                            </span>
                          ) : '—'}
                        </td>
                        <td>{r.capture_type || '—'}</td>
                        <td>{r.nstt_type || '—'}</td>
                        <td>{r.timing_type || '—'}</td>
                        <td>{r.diff_nstt_category || '—'}</td>
                        <td>
                          {r.exception_type ? (
                            <span className="pill-warning" title={r.exception_type}>
                              {r.exception_type}
                            </span>
                          ) : '—'}
                        </td>
                        <td>
                          {r.failure_category ? (
                            <span className="pill-error" title={r.failure_category}>
                              {r.failure_category}
                            </span>
                          ) : '—'}
                        </td>
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
