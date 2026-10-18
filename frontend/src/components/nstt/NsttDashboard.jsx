import React from 'react'
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
    warnings,
    namoFile,
    remedyFile,
    reset,
    handleExport,
  } = useNstt()

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
          <button
            type="button"
            className="export-excel-btn"
            onClick={handleExport}
            title="Download NSTT_Output.xlsx"
          >
            <span aria-hidden="true">📊</span> Export Excel
          </button>
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
