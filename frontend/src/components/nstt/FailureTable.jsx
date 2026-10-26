import { useNstt } from '../../context/NsttContext'
import './FailureTable.css'

/**
 * FailureTable — Table 2: Manually tagged – NSTT Before SR Creation
 *
 * 3-column table:
 *   Failure Category | Count | Percentage
 *
 * Dark blue header (#1F4E78), white bold text, thin borders.
 * Rows: Ring Failure | Section Failure | Unstitched | Others | Grand Total (83)
 */
export default function FailureTable() {
  const { aggregatedResult, openDrilldown, highlightedBifurcationKeys } = useNstt()

  if (!aggregatedResult || !aggregatedResult.failures) return null

  const failures = aggregatedResult.failures || {}
  const ring = failures.ring_failure || 0
  const section = failures.section_failure || 0
  const unstitched = failures.unstitched || 0
  const grandTotal = failures.grand_total || 0
  const others = failures.others != null ? failures.others : Math.max(0, grandTotal - (ring + section + unstitched))

  const manBefore = aggregatedResult.manual?.before_sr_creation || {}

  const pct = (val) => {
    if (grandTotal <= 0) return '—'
    return `${((val / grandTotal) * 100).toFixed(1)}%`
  }

  const rows = [
    { key: 'failures.ring_failure', label: 'Ring Failure', count: ring },
    { key: 'failures.section_failure', label: 'Section Failure', count: section },
    { key: 'failures.unstitched', label: 'Unstitched', count: unstitched },
    { key: 'failures.others', label: 'Others', count: others },
  ]

  return (
    <div className="spec-fail-wrapper" id="nstt-failure-analysis">
      {/* Title */}
      <div className="spec-fail-title-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <span className="spec-fail-title">Manually tagged – NSTT Before SR Creation</span>
        <div className="spec-tag-chips" style={{ display: 'inline-flex', gap: '8px' }}>
          <span className="spec-tag-chip" style={{ background: '#255d8f', color: '#ffffff', padding: '3px 10px', borderRadius: '4px', fontSize: '0.8rem' }}>
            SA: <strong style={{ color: '#ffffff' }}>{(manBefore.sa || 0).toLocaleString()}</strong>
          </span>
          <span className="spec-tag-chip" style={{ background: '#255d8f', color: '#ffffff', padding: '3px 10px', borderRadius: '4px', fontSize: '0.8rem' }}>
            NSA: <strong style={{ color: '#ffffff' }}>{(manBefore.nsa || 0).toLocaleString()}</strong>
          </span>
        </div>
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
            {rows.map((r) => {
              const isHighlighted = Boolean(highlightedBifurcationKeys?.has(r.key))
              return (
                <tr key={r.key} className="spec-fail-row">
                  <td className="spec-fail-td spec-fail-td-cat">
                    <span className="spec-fail-dot" aria-hidden="true" />
                    {r.label}
                  </td>
                  <td className={`spec-fail-td spec-fail-td-num${isHighlighted ? ' bifurcation-cell-highlighted' : ''}`}>
                    <button
                      type="button"
                      className={`spec-fail-btn${isHighlighted ? ' bifurcation-highlighted' : ''}`}
                      onClick={() => openDrilldown(r.key)}
                      title={`View ${r.count} records`}
                    >
                      {r.count.toLocaleString()}
                    </button>
                  </td>
                  <td className="spec-fail-td spec-fail-td-pct">{pct(r.count)}</td>
                </tr>
              )
            })}
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
