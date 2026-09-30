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

      {/* ── Warnings ribbon ────────────────────────────────────── */}
      {warnings && warnings.length > 0 && (
        <div className="dash-warnings-box" role="alert">
          <span className="warning-icon" aria-hidden="true">⚠️</span>
          <div className="warning-texts">
            {warnings.map((w, i) => <p key={i}>{w}</p>)}
          </div>
        </div>
      )}

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
