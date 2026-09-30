import React, { useState, useMemo } from 'react'
import { useNstt } from '../../context/NsttContext'
import './RawDataViewer.css'

export default function RawDataViewer() {
  const { classifiedMasterResponse, masterResponse } = useNstt()

  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const records = useMemo(() => {
    return classifiedMasterResponse?.records || masterResponse?.records || []
  }, [classifiedMasterResponse, masterResponse])

  // Get all columns from first record
  const allColumns = useMemo(() => {
    if (!records.length) return []
    return Object.keys(records[0])
  }, [records])

  // Filter records based on search term
  const filteredRecords = useMemo(() => {
    if (!searchTerm.trim()) return records
    const term = searchTerm.toLowerCase()
    return records.filter((rec) => {
      return Object.values(rec).some((val) =>
        String(val ?? '').toLowerCase().includes(term)
      )
    })
  }, [records, searchTerm])

  const totalRecords = filteredRecords.length
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize))

  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredRecords.slice(start, start + pageSize)
  }, [filteredRecords, currentPage, pageSize])

  const exportCsv = () => {
    if (!filteredRecords.length) return
    const headers = allColumns
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
    link.download = `NSTT_Raw_Dataset_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (!records.length) {
    return (
      <div className="raw-data-card empty-state-box">
        <span className="empty-icon">📂</span>
        <h3>No Enriched Dataset Available</h3>
        <p>Upload and process Namo and Remedy files to view the enriched dataset.</p>
      </div>
    )
  }

  return (
    <div className="raw-data-card" id="nstt-raw-data">
      <div className="raw-data-header">
        <div>
          <span className="card-badge">Enriched Data Layer</span>
          <h3>Final Enriched Dataset (Namo + Remedy)</h3>
          <p className="card-sub">
            Contains all Namo columns and 5 joined Remedy columns with classification attributes.
          </p>
        </div>

        <button type="button" className="btn-raw-export" onClick={exportCsv}>
          ⬇ Export Full CSV
        </button>
      </div>

      {/* Search & Pagination Controls */}
      <div className="raw-data-controls">
        <div className="raw-search-box">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            placeholder="Search across all fields..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1)
            }}
          />
          {searchTerm && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => setSearchTerm('')}
            >
              ✕
            </button>
          )}
        </div>

        <div className="raw-page-size">
          <label htmlFor="raw-page-select">Per page:</label>
          <select
            id="raw-page-select"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setCurrentPage(1)
            }}
          >
            <option value={15}>15</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="raw-table-wrapper">
        <table className="raw-table">
          <thead>
            <tr>
              <th className="sticky-col">#</th>
              {allColumns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedRecords.map((rec, idx) => {
              const rowNum = (currentPage - 1) * pageSize + idx + 1
              return (
                <tr key={rec.INCIDENTID || idx}>
                  <td className="sticky-col text-muted font-mono">{rowNum}</td>
                  {allColumns.map((col) => {
                    const val = rec[col]
                    let rendered = String(val ?? '')
                    if (val === true) rendered = 'TRUE'
                    if (val === false) rendered = 'FALSE'
                    if (val === null || val === undefined || rendered === '') rendered = '—'

                    return (
                      <td key={col} title={String(val ?? '')}>
                        {rendered.length > 50 ? `${rendered.slice(0, 50)}...` : rendered}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="raw-data-footer">
        <span className="pagination-info">
          Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords.toLocaleString()} records
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
    </div>
  )
}
