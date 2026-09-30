import React from 'react'
import { useNstt } from '../../context/NsttContext'
import './FailureTable.css'

/**
 * FailureTable — matches Sample_Output_UI_Specification.md §14
 *
 * Simple 3-column table:
 *   Failure Category | Count | Percentage
 *
 * Dark blue header (#1F4E78), white bold text, thin borders.
 * Rows: NSTT Number not found in Remedy | Ring Failure | Section Failure | Unstitched | Grand Total
 */
export default function FailureTable() {
  const { aggregatedResult, openDrilldown } = useNstt()

  if (!aggregatedResult || !aggregatedResult.failures) return null

  const failures   = aggregatedResult.failures
  const notFound   = failures.nstt_not_found    || 0
  const ring       = failures.ring_failure       || 0
  const section    = failures.section_failure    || 0
  const unstitched = failures.unstitched         || 0
  const grandTotal = failures.grand_total        || (notFound + ring + section + unstitched)

  const pct = (val) => {
    if (grandTotal <= 0) return '—'
    return `${((val / grandTotal) * 100).toFixed(1)}%`
  }

  const rows = [
    { key: 'failures.nstt_not_found', label: 'NSTT Number not found in Remedy', count: notFound },
    { key: 'failures.ring_failure',   label: 'Ring Failure',                    count: ring },
    { key: 'failures.section_failure', label: 'Section Failure',                count: section },
    { key: 'failures.unstitched',      label: 'Unstitched',                     count: unstitched },
  ]

  return (
    <div className="spec-fail-wrapper" id="nstt-failure-analysis">
      {/* Title */}
      <div className="spec-fail-title-bar">
        <span className="spec-fail-title">Failure Category</span>
      </div>

      {/* Table */}
      <div className="spec-fail-scroll">
        <table className="spec-fail-table">
          <thead>
            <tr className="spec-fail-hdr-row">
              <th className="spec-fail-th spec-fail-th-cat">Failure Category</th>
              <th className="spec-fail-th">Count</th>
              <th className="spec-fail-th">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="spec-fail-row">
                <td className="spec-fail-td spec-fail-td-cat">
                  <span className="spec-fail-dot" aria-hidden="true" />
                  {r.label}
                </td>
                <td className="spec-fail-td spec-fail-td-num">
                  <button
                    type="button"
                    className="spec-fail-btn"
                    onClick={() => openDrilldown(r.key)}
                    title={`View ${r.count} records`}
                  >
                    {r.count.toLocaleString()}
                  </button>
                </td>
                <td className="spec-fail-td spec-fail-td-pct">{pct(r.count)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="spec-fail-total-row">
              <td className="spec-fail-td spec-fail-td-cat spec-fail-total-label">Grand Total</td>
              <td className="spec-fail-td spec-fail-td-num">
                <button
                  type="button"
                  className="spec-fail-btn spec-fail-btn-total"
                  onClick={() => openDrilldown('failures.grand_total')}
                  title={`View all ${grandTotal} failure records`}
                >
                  {grandTotal.toLocaleString()}
                </button>
              </td>
              <td className="spec-fail-td spec-fail-td-pct spec-fail-total-label">100%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
