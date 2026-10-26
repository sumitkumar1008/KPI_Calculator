import React, { useEffect } from 'react'
import { useNstt } from '../../context/NsttContext'
import { extractIncidentId, extractSrNumber } from '../../utils/nsttBifurcationLocator'
import './NsttSummaryTable.css'

/**
 * NsttSummaryTable
 *
 * Renders the hierarchical matrix exactly as specified in Sample_Output_UI_Specification.md:
 *
 * Column structure (left → right, 12 total columns):
 *   1. Total SR (rowSpan 14)
 *   2. NSTT Count (rowSpan 14)
 *   3. Percentage NSTT Count (rowSpan 14)
 *   4-5. Sub Bifurcation (Type, Count (%))
 *   6-7. Further Bifurcation (Category, Count (%))
 *   8-9. Sub Sub Bifurcation (Type, Count (%))
 *   10-12. Detailed Bifurcation (Type, SA NSTT, NSA NSTT)
 *
 * Features:
 *   - Bifurcation Search Bar: searching any Incident ID or SR Number changes the color
 *     and smoothly centers it in view.
 *   - Clickable counts open the drilldown drawer for that category.
 */

const TableContext = React.createContext({
  openDrilldown: () => {},
  isKeyHighlighted: () => false,
  calcSubPct: () => '–',
  cnt: (v) => (v == null ? 0 : v),
})

/** Reusable count button with solid highlighted color (no blinking) */
const CountBtn = ({ catKey, cls = '', count, title, onClick }) => {
  const { openDrilldown, isKeyHighlighted, cnt } = React.useContext(TableContext)
  const isHighlighted = isKeyHighlighted(catKey)
  return (
    <button
      type="button"
      className={`spec-count-btn${cls ? ' ' + cls : ''}${isHighlighted ? ' bifurcation-highlighted' : ''}`}
      onClick={onClick || (() => openDrilldown(catKey))}
      title={title || `View ${cnt(count)} records`}
      data-cat-key={catKey}
    >
      {cnt(count).toLocaleString()}
    </button>
  )
}

/** SA + NSA + Unknown triad with count and percentage in the same row */
const ImpactBreakdown = ({ saKey, nsaKey, unknownKey, sa, nsa, unknown }) => {
  const { isKeyHighlighted, calcSubPct, cnt } = React.useContext(TableContext)
  return (
    <>
      <td className={`spec-td spec-count${isKeyHighlighted(saKey) ? ' bifurcation-cell-highlighted' : ''}`}>
        <CountBtn catKey={saKey} cls="sa" count={sa} title={`SA: ${cnt(sa)}`} />
        <span className="spec-pct-sub">{calcSubPct(sa)}</span>
      </td>
      <td className={`spec-td spec-count${isKeyHighlighted(nsaKey) ? ' bifurcation-cell-highlighted' : ''}`}>
        <CountBtn catKey={nsaKey} cls="nsa" count={nsa} title={`NSA: ${cnt(nsa)}`} />
        <span className="spec-pct-sub">{calcSubPct(nsa)}</span>
      </td>
      <td className={`spec-td spec-count${isKeyHighlighted(unknownKey) ? ' bifurcation-cell-highlighted' : ''}`}>
        <CountBtn catKey={unknownKey} cls="unknown" count={unknown} title={`Impact Unknown / Not Found in Remedy: ${cnt(unknown)}`} />
        <span className="spec-pct-sub">{calcSubPct(unknown)}</span>
      </td>
    </>
  )
}

/** Plain text cell */
const TC = ({ children, rowSpan, colSpan, cls }) => (
  <td
    className={`spec-td${cls ? ' ' + cls : ''}`}
    rowSpan={rowSpan}
    colSpan={colSpan}
  >
    {children}
  </td>
)

export default function NsttSummaryTable() {
  const {
    aggregatedResult,
    openDrilldown,
    bifurcationQuery,
    setBifurcationQuery,
    bifurcationResult,
    highlightedBifurcationKeys,
  } = useNstt()

  // Auto-scroll smooth locator effect when a match is found
  useEffect(() => {
    if (bifurcationResult?.allKeys?.length > 0) {
      const timer = setTimeout(() => {
        const highlightEl = document.querySelector('.bifurcation-highlighted, .bifurcation-cell-highlighted')
        if (highlightEl) {
          highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
        }
      }, 120)
      return () => clearTimeout(timer)
    }
  }, [bifurcationResult])

  if (!aggregatedResult) return null

  const {
    total_sr = 0,
    nstt_count = 0,
    nstt_percentage = 0,
    automation = {},
    manual = {},
    wrong_nstt = {},
    failures = {},
  } = aggregatedResult

  // --- Automation sub-trees ---
  const same = automation.same_nstt || {}
  const sameIm = same.im || {}
  const sameNonIm = same.non_im || {}
  const diff = automation.different_nstt || {}
  const resolved = automation.resolved_nstt || {}
  const resolvedIm = resolved.im || {}
  const resolvedNonIm = resolved.non_im || {}

  // --- Manual sub-trees ---
  const manBefore = manual.before_sr_creation || {}
  const manAfter = manual.after_sr_creation || {}
  const manResolved = manual.resolved || {}

  // Percentage and count helpers (all sub-percentages use nstt_count as base)
  const pct = (v) => (v == null ? '–' : `${v}%`)
  const cnt = (v) => (v == null ? 0 : v)
  const calcSubPct = (v) => (!nstt_count || nstt_count <= 0 || v == null ? '–' : `${((v / nstt_count) * 100).toFixed(1)}%`)

  // Check if a specific bifurcation key is currently highlighted
  const isKeyHighlighted = (key) => Boolean(key && highlightedBifurcationKeys?.has(key))

  const handleClearSearch = () => {
    if (setBifurcationQuery) setBifurcationQuery('')
  }

  return (
    <TableContext.Provider value={{ openDrilldown, isKeyHighlighted, calcSubPct, cnt }}>
    <div className="spec-dashboard-wrapper" id="nstt-summary-matrix">

      {/* ── Title bar ──────────────────────────────────────────── */}
      <div className="spec-title-bar">
        <span className="spec-title-badge">NSTT Dashboard</span>
        <div className="spec-title-actions">
          <span className="spec-eligible-pill">
            Eligible SRs (NSTT Count): <strong>{cnt(nstt_count).toLocaleString()}</strong> / {cnt(total_sr).toLocaleString()} ({pct(nstt_percentage)})
          </span>
        </div>
      </div>

      {/* ── Bifurcation Locator & Search Bar ────────────────────── */}
      <div className="spec-locator-section">
        <div className="spec-locator-bar">
          <div className="spec-locator-input-wrapper">
            <span className="spec-locator-icon" aria-hidden="true">🔎</span>
            <input
              type="text"
              id="nstt-bifurcation-search"
              className="spec-locator-input"
              value={bifurcationQuery || ''}
              onChange={(e) => setBifurcationQuery(e.target.value)}
              placeholder="Search Incident ID or SR Number to locate bifurcation..."
              autoComplete="off"
              spellCheck="false"
            />
            {bifurcationQuery && (
              <button
                type="button"
                className="spec-locator-clear-btn"
                onClick={handleClearSearch}
                title="Clear search"
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>
          <span className="spec-locator-hint">
            Type any Incident ID or SR Number to highlight which bifurcation it belongs to.
          </span>
        </div>

        {/* ── Search Match Result Banner ── */}
        {bifurcationQuery && bifurcationQuery.trim() && (
          <div className="spec-locator-results" role="status" aria-live="polite">
            {bifurcationResult && bifurcationResult.totalMatches > 0 ? (
              <div className="spec-locator-match-card">
                <div className="spec-match-header">
                  <span className="spec-match-badge">
                    <span className="spec-pulse-dot" />
                    {bifurcationResult.totalMatches === 1
                      ? `Located 1 record for "${bifurcationQuery}"`
                      : `Located ${bifurcationResult.totalMatches} records across ${bifurcationResult.bifurcations.length} bifurcation${bifurcationResult.bifurcations.length > 1 ? 's' : ''}`}
                  </span>
                  <span className="spec-match-hint">🎯 Particular box highlighted below in the matrix</span>
                </div>

                <div className="spec-match-list">
                  {bifurcationResult.bifurcations.map((bif, idx) => (
                    <div key={bif.key || idx} className="spec-match-item">
                      <div className="spec-match-breadcrumbs">
                        <span className="spec-match-target-icon">🎯</span>
                        {bif.breadcrumbs.map((crumb, cIdx) => (
                          <React.Fragment key={cIdx}>
                            <span className="spec-match-crumb">{crumb}</span>
                            {cIdx < bif.breadcrumbs.length - 1 && <span className="spec-match-arrow">➔</span>}
                          </React.Fragment>
                        ))}
                        {bif.records && bif.records.length > 0 && (
                          <span className="spec-match-record-chip">
                            {bif.records.length} record{bif.records.length > 1 ? 's' : ''}
                            {bif.records[0] && (
                              <>
                                {' '}(Incident: <strong>{extractIncidentId(bif.records[0]) || '—'}</strong> | SR: <strong>{extractSrNumber(bif.records[0]) || '—'}</strong>)
                              </>
                            )}
                          </span>
                        )}
                      </div>
                      <div className="spec-match-actions">
                        <button
                          type="button"
                          className="spec-match-view-btn"
                          onClick={() => openDrilldown(bif.key)}
                          title={`Open drill-down for ${bif.label}`}
                        >
                          View in Drilldown ↗
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="spec-locator-no-match">
                <span className="spec-no-match-icon">⚠️</span>
                <span>
                  No Incident ID or SR Number matching <strong>&ldquo;{bifurcationQuery}&rdquo;</strong> found in the current dataset.
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Main hierarchical matrix ──────────────────────────── */}
      <div className="spec-table-scroll">
        <table className="spec-matrix-table">

          {/* ── HEADER ── */}
          <thead>
            {/* Row 1: top-level column groups */}
            <tr className="spec-hdr-row">
              <th className="spec-th" rowSpan={2}>Total SR</th>
              <th className="spec-th" rowSpan={2}>NSTT Count</th>
              <th className="spec-th" rowSpan={2}>Percentage NSTT Count</th>
              {/* Sub Bifurcation */}
              <th className="spec-th" colSpan={2}>Sub Bifurcation</th>
              {/* Further Bifurcation */}
              <th className="spec-th" colSpan={2}>Further Bifurcation</th>
              {/* Sub Sub Bifurcation */}
              <th className="spec-th" colSpan={2}>Sub Sub Bifurcation</th>
              {/* Detailed Bifurcation (Auto/Manual SR Count) */}
              <th className="spec-th" colSpan={2}>Detailed Bifurcation</th>
              {/* Sub Sub Sub Bifurcation (3-part Impact: SA, NSA, Unknown) */}
              <th className="spec-th" colSpan={3}>Sub Sub Sub Bifurcation</th>
            </tr>
            {/* Row 2: sub-column labels */}
            <tr className="spec-hdr-row">
              <th className="spec-th spec-th-sub">Type</th>
              <th className="spec-th spec-th-sub">Count (%)</th>
              <th className="spec-th spec-th-sub">Category</th>
              <th className="spec-th spec-th-sub">Count (%)</th>
              <th className="spec-th spec-th-sub">Type</th>
              <th className="spec-th spec-th-sub">Count (%)</th>
              <th className="spec-th spec-th-sub">Type</th>
              <th className="spec-th spec-th-sub">Count (%)</th>
              <th className="spec-th spec-th-sub">SA NSTT Count (%)</th>
              <th className="spec-th spec-th-sub">NSA NSTT Count (%)</th>
              <th className="spec-th spec-th-sub">Impact Unknown / Not Found in Remedy</th>
            </tr>
          </thead>

          <tbody>

            {/* ════════════════════════════════════════════════════════
                AUTOMATION CAPTURED — 10 rows (Same: 4, Diff: 1, Res: 4, Wrong: 1)
                ════════════════════════════════════════════════════════ */}

            {/* Row 1: Auto > Same NSTT > IM > Auto */}
            <tr className="spec-row spec-row-auto-start">
              {/* Total SR — spans all 15 rows */}
              <td className={`spec-td spec-cell-total${isKeyHighlighted('total_sr') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={15}>
                <CountBtn catKey="total_sr" cls="total" count={total_sr} title="Drilldown: Total SR" />
              </td>
              {/* NSTT Count */}
              <td className={`spec-td spec-cell-nstt${isKeyHighlighted('nstt_count') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={15}>
                <CountBtn catKey="nstt_count" cls="nstt" count={nstt_count} title="Drilldown: NSTT Count" />
              </td>
              {/* Percentage NSTT Count */}
              <td className="spec-td spec-cell-pct" rowSpan={15}>
                {pct(nstt_percentage)}
              </td>

              {/* Sub Bif: Automation Captured (spans 10 automation rows) */}
              <TC cls="spec-cell-auto spec-label-bold" rowSpan={10}>Automation Captured</TC>
              <td className={`spec-td spec-count spec-cell-auto${isKeyHighlighted('automation') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={10}>
                <CountBtn catKey="automation" count={automation.count} />
                <span className="spec-pct-sub">{pct(automation.percentage)}</span>
              </td>

              {/* Further Bif: Same NSTT (spans 4 rows) */}
              <TC cls="spec-label-med" rowSpan={4}>Auto Capture – Same NSTT</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={4}>
                <CountBtn catKey="automation.same_nstt" count={same.count} />
                <span className="spec-pct-sub">{pct(same.percentage)}</span>
              </td>

              {/* Sub Sub Bif: IM (spans 2 rows) */}
              <TC rowSpan={2}>IM</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.im') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={2}>
                <CountBtn catKey="automation.same_nstt.im" count={sameIm.count} />
                <span className="spec-pct-sub">{pct(sameIm.percentage)}</span>
              </td>

              {/* Detailed: IM > Auto */}
              <TC>Auto</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.im.auto') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.same_nstt.im.auto" count={sameIm.auto?.count} />
                <span className="spec-pct-sub">{calcSubPct(sameIm.auto?.count)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.same_nstt.im.auto.sa"
                nsaKey="automation.same_nstt.im.auto.nsa"
                unknownKey="automation.same_nstt.im.auto.unknown"
                sa={sameIm.auto?.sa}
                nsa={sameIm.auto?.nsa}
                unknown={sameIm.auto?.unknown}
              />
            </tr>

            {/* Row 2: Auto > Same NSTT > IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.im.manual') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.same_nstt.im.manual" count={sameIm.manual?.count} />
                <span className="spec-pct-sub">{calcSubPct(sameIm.manual?.count)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.same_nstt.im.manual.sa"
                nsaKey="automation.same_nstt.im.manual.nsa"
                unknownKey="automation.same_nstt.im.manual.unknown"
                sa={sameIm.manual?.sa}
                nsa={sameIm.manual?.nsa}
                unknown={sameIm.manual?.unknown}
              />
            </tr>

            {/* Row 3: Auto > Same NSTT > Non IM > Auto */}
            <tr className="spec-row">
              <TC rowSpan={2}>Non IM</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.non_im') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={2}>
                <CountBtn catKey="automation.same_nstt.non_im" count={sameNonIm.count} />
                <span className="spec-pct-sub">{pct(sameNonIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.non_im.auto') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.same_nstt.non_im.auto" count={sameNonIm.auto?.count} />
                <span className="spec-pct-sub">{calcSubPct(sameNonIm.auto?.count)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.same_nstt.non_im.auto.sa"
                nsaKey="automation.same_nstt.non_im.auto.nsa"
                unknownKey="automation.same_nstt.non_im.auto.unknown"
                sa={sameNonIm.auto?.sa}
                nsa={sameNonIm.auto?.nsa}
                unknown={sameNonIm.auto?.unknown}
              />
            </tr>

            {/* Row 4: Auto > Same NSTT > Non IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.same_nstt.non_im.manual') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.same_nstt.non_im.manual" count={sameNonIm.manual?.count} />
                <span className="spec-pct-sub">{calcSubPct(sameNonIm.manual?.count)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.same_nstt.non_im.manual.sa"
                nsaKey="automation.same_nstt.non_im.manual.nsa"
                unknownKey="automation.same_nstt.non_im.manual.unknown"
                sa={sameNonIm.manual?.sa}
                nsa={sameNonIm.manual?.nsa}
                unknown={sameNonIm.manual?.unknown}
              />
            </tr>

            {/* ── Row 5: Different NSTT ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Auto Capture – Different NSTT</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.different_nstt') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.different_nstt" count={diff.count} />
                <span className="spec-pct-sub">{pct(diff.percentage)}</span>
              </td>
              {/* Sub Sub Bifurcation: Type (5 categories) */}
              <td className="spec-td spec-subsub-types-cell">
                <div className="spec-subsub-type-list">
                  <div className="spec-subsub-item">Incident SA auto NSA</div>
                  <div className="spec-subsub-item">Incident NSA auto SA</div>
                  <div className="spec-subsub-item">Both NSA</div>
                  <div className="spec-subsub-item">Both SA</div>
                  <div className="spec-subsub-item">Impact Unknown / Not Found in Remedy</div>
                </div>
              </td>
              {/* Sub Sub Bifurcation: Count (%) (Calculated with base nstt_count) */}
              <td className="spec-td spec-count spec-subsub-counts-cell">
                <div className="spec-subsub-count-list">
                  <div className={`spec-subsub-item${isKeyHighlighted('automation.different_nstt.incident_sa_auto_nsa') ? ' bifurcation-cell-highlighted' : ''}`}>
                    <CountBtn catKey="automation.different_nstt.incident_sa_auto_nsa" count={diff.incident_sa_auto_nsa} />
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_sa_auto_nsa)}</span>
                  </div>
                  <div className={`spec-subsub-item${isKeyHighlighted('automation.different_nstt.incident_nsa_auto_sa') ? ' bifurcation-cell-highlighted' : ''}`}>
                    <CountBtn catKey="automation.different_nstt.incident_nsa_auto_sa" count={diff.incident_nsa_auto_sa} />
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_nsa_auto_sa)}</span>
                  </div>
                  <div className={`spec-subsub-item${isKeyHighlighted('automation.different_nstt.both_nsa') ? ' bifurcation-cell-highlighted' : ''}`}>
                    <CountBtn catKey="automation.different_nstt.both_nsa" count={diff.both_nsa} />
                    <span className="spec-pct-sub">{calcSubPct(diff.both_nsa)}</span>
                  </div>
                  <div className={`spec-subsub-item${isKeyHighlighted('automation.different_nstt.both_sa') ? ' bifurcation-cell-highlighted' : ''}`}>
                    <CountBtn catKey="automation.different_nstt.both_sa" count={diff.both_sa} />
                    <span className="spec-pct-sub">{calcSubPct(diff.both_sa)}</span>
                  </div>
                  <div className={`spec-subsub-item${isKeyHighlighted('automation.different_nstt.unknown') ? ' bifurcation-cell-highlighted' : ''}`}>
                    <CountBtn catKey="automation.different_nstt.unknown" count={diff.unknown} />
                    <span className="spec-pct-sub">{calcSubPct(diff.unknown)}</span>
                  </div>
                </div>
              </td>
              {/* Detailed Bifurcation: 2 cols, Sub Sub Sub Bifurcation: 3 cols */}
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* ── Rows 6..9: Resolved NSTT > IM (Auto / Manual) & Non IM (Auto / Manual) ── */}
            {/* Row 6: Resolved > IM > Auto */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med" rowSpan={4}>Auto Capture – Resolved NSTT</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={4}>
                <CountBtn catKey="automation.resolved_nstt" count={resolved.count} />
                <span className="spec-pct-sub">{pct(resolved.percentage)}</span>
              </td>
              <TC rowSpan={2}>IM</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.im') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={2}>
                <CountBtn
                  catKey="automation.resolved_nstt.im"
                  count={resolvedIm.count ?? ((resolvedIm.auto?.count ?? resolvedIm.auto ?? 0) + (resolvedIm.manual?.count ?? resolvedIm.manual ?? 0))}
                />
                <span className="spec-pct-sub">{pct(resolvedIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.im.auto') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.resolved_nstt.im.auto" count={resolvedIm.auto?.count ?? resolvedIm.auto} />
                <span className="spec-pct-sub">{calcSubPct(resolvedIm.auto?.count ?? resolvedIm.auto)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.resolved_nstt.im.auto.sa"
                nsaKey="automation.resolved_nstt.im.auto.nsa"
                unknownKey="automation.resolved_nstt.im.auto.unknown"
                sa={resolvedIm.auto?.sa}
                nsa={resolvedIm.auto?.nsa}
                unknown={resolvedIm.auto?.unknown}
              />
            </tr>

            {/* Row 7: Resolved > IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.im.manual') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.resolved_nstt.im.manual" count={resolvedIm.manual?.count ?? resolvedIm.manual} />
                <span className="spec-pct-sub">{calcSubPct(resolvedIm.manual?.count ?? resolvedIm.manual)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.resolved_nstt.im.manual.sa"
                nsaKey="automation.resolved_nstt.im.manual.nsa"
                unknownKey="automation.resolved_nstt.im.manual.unknown"
                sa={resolvedIm.manual?.sa}
                nsa={resolvedIm.manual?.nsa}
                unknown={resolvedIm.manual?.unknown}
              />
            </tr>

            {/* Row 8: Resolved > Non IM > Auto */}
            <tr className="spec-row">
              <TC rowSpan={2}>Non IM</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.non_im') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={2}>
                <CountBtn
                  catKey="automation.resolved_nstt.non_im"
                  count={resolvedNonIm.count ?? ((resolvedNonIm.auto?.count ?? resolvedNonIm.auto ?? 0) + (resolvedNonIm.manual?.count ?? resolvedNonIm.manual ?? 0))}
                />
                <span className="spec-pct-sub">{pct(resolvedNonIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.non_im.auto') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.resolved_nstt.non_im.auto" count={resolvedNonIm.auto?.count ?? resolvedNonIm.auto} />
                <span className="spec-pct-sub">{calcSubPct(resolvedNonIm.auto?.count ?? resolvedNonIm.auto)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.resolved_nstt.non_im.auto.sa"
                nsaKey="automation.resolved_nstt.non_im.auto.nsa"
                unknownKey="automation.resolved_nstt.non_im.auto.unknown"
                sa={resolvedNonIm.auto?.sa}
                nsa={resolvedNonIm.auto?.nsa}
                unknown={resolvedNonIm.auto?.unknown}
              />
            </tr>

            {/* Row 9: Resolved > Non IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('automation.resolved_nstt.non_im.manual') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="automation.resolved_nstt.non_im.manual" count={resolvedNonIm.manual?.count ?? resolvedNonIm.manual} />
                <span className="spec-pct-sub">{calcSubPct(resolvedNonIm.manual?.count ?? resolvedNonIm.manual)}</span>
              </td>
              <ImpactBreakdown
                saKey="automation.resolved_nstt.non_im.manual.sa"
                nsaKey="automation.resolved_nstt.non_im.manual.nsa"
                unknownKey="automation.resolved_nstt.non_im.manual.unknown"
                sa={resolvedNonIm.manual?.sa}
                nsa={resolvedNonIm.manual?.nsa}
                unknown={resolvedNonIm.manual?.unknown}
              />
            </tr>

            {/* ── Row 10: Wrong NSTT by Automation (1 row) ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Wrong NSTT Attached by Automation Ang in TXN Attribution</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('wrong_nstt.automation_ang_txn') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="wrong_nstt.automation_ang_txn" count={wrong_nstt.automation_ang_txn} />
                <span className="spec-pct-sub">{calcSubPct(wrong_nstt.automation_ang_txn)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* ════════════════════════════════════════════════════════
                MANUAL CAPTURED — 5 rows (Before: 1, After: 1, Res: 1, Wrong: 1, NSTT not found: 1)
                ════════════════════════════════════════════════════════ */}

            {/* Row 11: Manual > Before SR Creation */}
            <tr className="spec-row spec-row-manual-start">
              <TC cls="spec-cell-manual spec-label-bold" rowSpan={5}>Manual Captured</TC>
              <td className={`spec-td spec-count spec-cell-manual${isKeyHighlighted('manual') ? ' bifurcation-cell-highlighted' : ''}`} rowSpan={5}>
                <CountBtn catKey="manual" cls="manual" count={manual.count} />
                <span className="spec-pct-sub">{pct(manual.percentage)}</span>
              </td>
              <TC cls="spec-label-med">Manual NSTT Before SR Creation</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('manual.before_sr_creation') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="manual.before_sr_creation" count={manBefore.count} />
                <span className="spec-pct-sub">{pct(manBefore.percentage)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <ImpactBreakdown
                saKey="manual.before_sr_creation.sa"
                nsaKey="manual.before_sr_creation.nsa"
                unknownKey="manual.before_sr_creation.unknown"
                sa={manBefore.sa}
                nsa={manBefore.nsa}
                unknown={manBefore.unknown}
              />
            </tr>

            {/* Row 12: Manual > After SR Creation */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT After SR Creation</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('manual.after_sr_creation') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="manual.after_sr_creation" count={manAfter.count} />
                <span className="spec-pct-sub">{pct(manAfter.percentage)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <ImpactBreakdown
                saKey="manual.after_sr_creation.sa"
                nsaKey="manual.after_sr_creation.nsa"
                unknownKey="manual.after_sr_creation.unknown"
                sa={manAfter.sa}
                nsa={manAfter.nsa}
                unknown={manAfter.unknown}
              />
            </tr>

            {/* Row 13: Manual > Resolved */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT Resolved</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('manual.resolved') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="manual.resolved" count={manResolved.count} />
                <span className="spec-pct-sub">{pct(manResolved.percentage)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <ImpactBreakdown
                saKey="manual.resolved.sa"
                nsaKey="manual.resolved.nsa"
                unknownKey="manual.resolved.unknown"
                sa={manResolved.sa}
                nsa={manResolved.nsa}
                unknown={manResolved.unknown}
              />
            </tr>

            {/* Row 14: Wrong NSTT by Engineer */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Wrong NSTT Attached by Engineer Ang in TXN Attribution</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('wrong_nstt.engineer_ang_txn') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="wrong_nstt.engineer_ang_txn" count={wrong_nstt.engineer_ang_txn} />
                <span className="spec-pct-sub">{calcSubPct(wrong_nstt.engineer_ang_txn)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* Row 15: NSTT Number not found in Remedy */}
            <tr className="spec-row">
              <TC cls="spec-label-med">NSTT Number not found in Remedy</TC>
              <td className={`spec-td spec-count${isKeyHighlighted('failures.nstt_not_found') ? ' bifurcation-cell-highlighted' : ''}`}>
                <CountBtn catKey="failures.nstt_not_found" count={failures.nstt_not_found} />
                <span className="spec-pct-sub">{calcSubPct(failures.nstt_not_found)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

          </tbody>
        </table>
      </div>

    </div>
    </TableContext.Provider>
  )
}
