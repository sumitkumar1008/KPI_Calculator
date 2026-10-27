import { useState, useRef, useEffect } from 'react'
import { useNstt } from '../../context/NsttContext'
import NsttSummaryTable from './NsttSummaryTable'
import FailureTable from './FailureTable'
import NsttDrillDown from './NsttDrillDown'
import './nstt-dashboard.css'

/**
 * NsttDashboard — matches Sample_Output_UI_Specification.md
 *
 * Layout:
 *   ┌─ Compact top bar (title | file info | actions) ─────────────┐
 *   │  Warnings ribbon (if any)                                    │
 *   │  NsttSummaryTable   ← main hierarchical matrix              │
 *   │  FailureTable       ← failure category section              │
 *   └──────────────────────────────────────────────────────────────┘
 */
export default function NsttDashboard() {
  const {
    aggregatedResult,
    stats,
    namoFile,
    remedyFile,
    reset,
    handleExport,
  } = useNstt()

  const [isExportOpen, setIsExportOpen] = useState(false)
  const [exportingType, setExportingType] = useState(null)
  const exportDropdownRef = useRef(null)

  // Close dropdown on click outside or Escape key
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target)) {
        setIsExportOpen(false)
      }
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsExportOpen(false)
      }
    }

    if (isExportOpen) {
      document.addEventListener('mousedown', handleOutsideClick)
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isExportOpen])

  const triggerExport = async (type) => {
    if (exportingType) return
    setExportingType(type)
    try {
      await handleExport(type)
    } catch {
      // Alert already handled in NsttContext
    } finally {
      setExportingType(null)
      setIsExportOpen(false)
    }
  }

  if (!aggregatedResult) return null

  return (
    <section className="nstt-dashboard-container" aria-labelledby="nstt-dash-title">

      {/* ── Compact top header ─────────────────────────────────── */}
      <div className="nstt-dash-header">
        <div className="nstt-dash-header-left">
          <h2 id="nstt-dash-title" className="nstt-dash-title">NSTT Dashboard</h2>
          <p className="dash-sub">
            <span className="dash-file-pill">{namoFile?.name || 'Namo Report'}</span>
            <span className="dash-amp">&amp;</span>
            <span className="dash-file-pill">{remedyFile?.name || 'Remedy Report'}</span>
            {stats && (
              <span className="dash-matched"> • {stats.matched?.toLocaleString() || 0} matched records</span>
            )}
          </p>
        </div>
        <div className="dash-actions">
          {/* Active Export Dropdown with 2 options */}
          <div className="nstt-export-dropdown" ref={exportDropdownRef}>
            <button
              type="button"
              className={`export-excel-btn ${isExportOpen ? 'is-active' : ''}`}
              onClick={() => setIsExportOpen((prev) => !prev)}
              disabled={Boolean(exportingType)}
              aria-expanded={isExportOpen}
              aria-haspopup="true"
              title="Download Excel reports"
            >
              {exportingType ? (
                <span className="export-btn-spinner" aria-hidden="true" />
              ) : (
                <span aria-hidden="true" className="export-btn-icon">📊</span>
              )}
              <span>
                {exportingType
                  ? exportingType === 'dashboard'
                    ? 'Exporting Dashboard...'
                    : exportingType === 'raw'
                    ? 'Exporting Raw Data...'
                    : 'Exporting...'
                  : 'Export Excel'}
              </span>
              <svg
                className={`export-chevron ${isExportOpen ? 'is-rotated' : ''}`}
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            {isExportOpen && (
              <div className="nstt-export-menu" role="menu" aria-label="Export options">
                <div className="nstt-export-menu-header">Select Export Option</div>

                {/* Option 1: Dashboard Table (formatted summary & failure table in excel sheet) */}
                <button
                  type="button"
                  className="nstt-export-item"
                  role="menuitem"
                  onClick={() => triggerExport('dashboard')}
                  disabled={Boolean(exportingType)}
                >
                  <div className="nstt-export-item-badge badge--dash" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <line x1="3" y1="9" x2="21" y2="9" />
                      <line x1="3" y1="15" x2="21" y2="15" />
                      <line x1="9" y1="3" x2="9" y2="21" />
                      <line x1="15" y1="3" x2="15" y2="21" />
                    </svg>
                  </div>
                  <div className="nstt-export-item-content">
                    <div className="nstt-export-item-title-row">
                      <span className="nstt-export-item-title">Dashboard Table</span>
                      <span className="nstt-export-file-tag">.XLSX</span>
                    </div>
                    <span className="nstt-export-item-desc">
                      Replicates the dashboard summary matrix &amp; failure table in an Excel sheet
                    </span>
                  </div>
                </button>

                {/* Option 2: Processed Raw data formed after V-lookup and operations (.csv) */}
                <button
                  type="button"
                  className="nstt-export-item"
                  role="menuitem"
                  onClick={() => triggerExport('csv')}
                  disabled={Boolean(exportingType)}
                >
                  <div className="nstt-export-item-badge badge--csv" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="8" y1="13" x2="16" y2="13" />
                      <line x1="8" y1="17" x2="16" y2="17" />
                    </svg>
                  </div>
                  <div className="nstt-export-item-content">
                    <div className="nstt-export-item-title-row">
                      <span className="nstt-export-item-title">Processed Raw Data</span>
                      <span className="nstt-export-file-tag tag--csv">.CSV</span>
                    </div>
                    <span className="nstt-export-item-desc">
                      Enriched dataset formed after V-lookup with all operations and classifications
                    </span>
                  </div>
                </button>
              </div>
            )}
          </div>

          <button type="button" className="upload-new-btn" onClick={reset}>
            <span aria-hidden="true">↺</span> New Upload
          </button>
        </div>
      </div>

      {/* ── Success Banner (records successfully fetched from both files) ── */}
      <div className="dash-success-box" role="status">
        <span className="dash-success-icon" aria-hidden="true">✓</span>
        <div className="dash-success-texts">
          <span>
            Total <strong>{((stats?.namo_rows || 0) + (stats?.remedy_rows || 0)).toLocaleString()} records</strong> have been successfully fetched from both files{' '}
            (<strong>{(stats?.namo_rows || 0).toLocaleString()}</strong> from {namoFile?.name || 'Namo Report'} &amp;{' '}
            <strong>{(stats?.remedy_rows || 0).toLocaleString()}</strong> from {remedyFile?.name || 'Remedy Report'})
            {stats?.matched != null && (
              <span className="dash-success-matched">
                ✓ {stats.matched.toLocaleString()} records successfully matched
              </span>
            )}
          </span>
        </div>
      </div>

      {/* ── Main Dashboard Content ─────────────────────────────── */}
      <div className="nstt-dashboard-content">
        {/* Main hierarchical matrix */}
        <NsttSummaryTable />
        {/* Failure Category section below */}
        <FailureTable />
      </div>

      {/* ── Record-level drill-down drawer ─────────────────────── */}
      <NsttDrillDown />
    </section>
  )
}
