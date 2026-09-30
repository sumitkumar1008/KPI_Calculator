import React from 'react'
import { useNstt } from '../../context/NsttContext'
import './NsttSummaryTable.css'

/**
 * NsttSummaryTable
 *
 * Renders the hierarchical matrix exactly as specified in Sample_Output_UI_Specification.md:
 *
 * Column structure (left → right):
 *   Total SR | NSTT Count | % of Total SR |
 *   Sub Bifurcation (Type / Count %) |
 *   Further Bifurcation (Category / Count %) |
 *   Sub Sub Bifurcation (Type / Count) |
 *   Detailed Bifurcation (SA / NSA)
 *
 * Headers: dark blue #1F4E78, white bold text, center-aligned, thin borders.
 * Data rows: merged cells vertically for parent categories (rowspan).
 * Clickable count badges for drill-down.
 */
export default function NsttSummaryTable() {
  const { aggregatedResult, openDrilldown } = useNstt()

  if (!aggregatedResult) return null

  const {
    total_sr = 0,
    nstt_count = 0,
    nstt_percentage = 0,
    automation = {},
    manual = {},
    wrong_nstt = {},
  } = aggregatedResult

  // --- Automation sub-trees ---
  const same       = automation.same_nstt         || {}
  const sameIm     = same.im                       || {}
  const sameNonIm  = same.non_im                   || {}
  const diff       = automation.different_nstt     || {}
  const resolved   = automation.resolved_nstt      || {}
  const resolvedIm    = resolved.im                || {}
  const resolvedNonIm = resolved.non_im            || {}

  // --- Manual sub-trees ---
  const manBefore  = manual.before_sr_creation     || {}
  const manAfter   = manual.after_sr_creation      || {}
  const manResolved = manual.resolved              || {}

  // Helpers
  const pct  = (v) => (v == null ? '–' : `${v}%`)
  const cnt  = (v) => (v == null ? 0 : v)
  const calcSubPct = (v, total) => (!total || total <= 0 || v == null ? '–' : `${((v / total) * 100).toFixed(1)}%`)

  /** Clickable count cell */
  const CC = ({ drillKey, value, extra }) => (
    <td className="spec-td spec-count">
      <button
        type="button"
        className="spec-count-btn"
        onClick={() => openDrilldown(drillKey)}
        title={`Drill down: ${drillKey}`}
      >
        {cnt(value).toLocaleString()}
      </button>
      {extra != null && <span className="spec-pct-sub">{pct(extra)}</span>}
    </td>
  )

  /** SA + NSA pair */
  const SaNsa = ({ saKey, nsaKey, sa, nsa }) => (
    <>
      <td className="spec-td spec-count">
        <button type="button" className="spec-count-btn sa" onClick={() => openDrilldown(saKey)}>{cnt(sa)}</button>
      </td>
      <td className="spec-td spec-count">
        <button type="button" className="spec-count-btn nsa" onClick={() => openDrilldown(nsaKey)}>{cnt(nsa)}</button>
      </td>
    </>
  )

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

  return (
    <div className="spec-dashboard-wrapper" id="nstt-summary-matrix">

      {/* ── Title bar ──────────────────────────────────────────── */}
      <div className="spec-title-bar">
        <span className="spec-title-badge">NSTT Dashboard</span>
        <div className="spec-title-actions">
          <span className="spec-eligible-pill">
            Eligible SRs: <strong>{cnt(nstt_count)}</strong> / {cnt(total_sr)}
          </span>
        </div>
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
              {/* Detailed Bifurcation (SA / NSA) */}
              <th className="spec-th" colSpan={3}>Detailed Bifurcation</th>
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
              <th className="spec-th spec-th-sub">SA NSTT</th>
              <th className="spec-th spec-th-sub">NSA NSTT</th>
            </tr>
          </thead>

          <tbody>

            {/* ════════════════════════════════════════════════════════
                AUTOMATION — rows 1..8  (rowspan 8)
                ════════════════════════════════════════════════════════ */}

            {/* Row 1: Auto > Same NSTT > IM > Auto */}
            <tr className="spec-row spec-row-auto-start">
              {/* Total SR — spans all automation rows (8) + manual rows (5) + wrong rows (2) */}
              <td className="spec-td spec-sticky spec-cell-total" rowSpan={17}>
                <button className="spec-count-btn total" onClick={() => openDrilldown('total_sr')}>
                  {cnt(total_sr).toLocaleString()}
                </button>
              </td>
              {/* NSTT Count */}
              <td className="spec-td spec-sticky spec-cell-nstt" rowSpan={17}>
                <button className="spec-count-btn nstt" onClick={() => openDrilldown('nstt_count')}>
                  {cnt(nstt_count).toLocaleString()}
                </button>
              </td>
              {/* Percentage NSTT Count */}
              <td className="spec-td spec-sticky spec-cell-pct" rowSpan={17}>
                {pct(nstt_percentage)}
              </td>

              {/* Sub Bif: Automation Captured (spans 8 automation rows) */}
              <TC cls="spec-cell-auto spec-label-bold" rowSpan={8}>Automation Captured</TC>
              <td className="spec-td spec-count spec-cell-auto" rowSpan={8}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation')}>
                  {cnt(automation.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(automation.percentage)}</span>
              </td>

              {/* Further Bif: Same NSTT (spans 4 rows) */}
              <TC cls="spec-label-med" rowSpan={4}>Auto Capture – Same NSTT</TC>
              <td className="spec-td spec-count" rowSpan={4}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.same_nstt')}>
                  {cnt(same.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(same.percentage)}</span>
              </td>

              {/* Sub Sub Bif: IM (spans 2 rows) */}
              <TC rowSpan={2}>IM</TC>
              <td className="spec-td spec-count" rowSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.same_nstt.im')}>
                  {cnt(sameIm.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(sameIm.percentage)}</span>
              </td>

              {/* Detailed: IM > Auto */}
              <TC>Auto</TC>
              <SaNsa
                saKey="automation.same_nstt.im.auto.sa"
                nsaKey="automation.same_nstt.im.auto.nsa"
                sa={sameIm.auto?.sa}
                nsa={sameIm.auto?.nsa}
              />
            </tr>

            {/* Row 2: Auto > Same NSTT > IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <SaNsa
                saKey="automation.same_nstt.im.manual.sa"
                nsaKey="automation.same_nstt.im.manual.nsa"
                sa={sameIm.manual?.sa}
                nsa={sameIm.manual?.nsa}
              />
            </tr>

            {/* Row 3: Auto > Same NSTT > Non IM > Auto */}
            <tr className="spec-row">
              {/* Sub Sub Bif: Non IM (spans 2 rows) */}
              <TC rowSpan={2}>Non IM</TC>
              <td className="spec-td spec-count" rowSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.same_nstt.non_im')}>
                  {cnt(sameNonIm.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(sameNonIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <SaNsa
                saKey="automation.same_nstt.non_im.auto.sa"
                nsaKey="automation.same_nstt.non_im.auto.nsa"
                sa={sameNonIm.auto?.sa}
                nsa={sameNonIm.auto?.nsa}
              />
            </tr>

            {/* Row 4: Auto > Same NSTT > Non IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <SaNsa
                saKey="automation.same_nstt.non_im.manual.sa"
                nsaKey="automation.same_nstt.non_im.manual.nsa"
                sa={sameNonIm.manual?.sa}
                nsa={sameNonIm.manual?.nsa}
              />
            </tr>

            {/* ── Different NSTT ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Auto Capture – Different NSTT</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt')}>
                  {cnt(diff.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(diff.percentage)}</span>
              </td>
              {/* Sub Sub Bifurcation: Type (4 categories aligned) */}
              <td className="spec-td spec-subsub-types-cell">
                <div className="spec-subsub-type-list">
                  <div className="spec-subsub-item">Incident SA auto NSA</div>
                  <div className="spec-subsub-item">Incident NSA auto SA</div>
                  <div className="spec-subsub-item">Both NSA</div>
                  <div className="spec-subsub-item">Both SA</div>
                </div>
              </td>
              {/* Sub Sub Bifurcation: Count (%) (Beside each category) */}
              <td className="spec-td spec-count spec-subsub-counts-cell">
                <div className="spec-subsub-count-list">
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.incident_sa_auto_nsa')}>
                      {cnt(diff.incident_sa_auto_nsa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_sa_auto_nsa, diff.count)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.incident_nsa_auto_sa')}>
                      {cnt(diff.incident_nsa_auto_sa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_nsa_auto_sa, diff.count)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.both_nsa')}>
                      {cnt(diff.both_nsa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.both_nsa, diff.count)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.both_sa')}>
                      {cnt(diff.both_sa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.both_sa, diff.count)}</span>
                  </div>
                </div>
              </td>
              {/* Detailed Bifurcation: 3 cols */}
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* ── Resolved NSTT > IM + Non IM ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med" rowSpan={2}>Auto Capture – Resolved NSTT</TC>
              <td className="spec-td spec-count" rowSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt')}>
                  {cnt(resolved.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolved.percentage)}</span>
              </td>
              <TC>IM</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.im')}>
                  {cnt(resolvedIm.count ?? ((resolvedIm.auto ?? 0) + (resolvedIm.manual ?? 0))).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolvedIm.percentage)}</span>
              </td>
              {/* Detailed Bifurcation: Auto / Manual across 3 cols */}
              <td className="spec-td" colSpan={3}>
                <div className="spec-chip-row">
                  <button className="spec-chip" onClick={() => openDrilldown('automation.resolved_nstt.im')}>
                    Auto: <strong>{cnt(resolvedIm.auto)}</strong>
                  </button>
                  <button className="spec-chip" onClick={() => openDrilldown('automation.resolved_nstt.im')}>
                    Manual: <strong>{cnt(resolvedIm.manual)}</strong>
                  </button>
                </div>
              </td>
            </tr>
            <tr className="spec-row">
              <TC>Non IM</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.non_im')}>
                  {cnt(resolvedNonIm.count ?? ((resolvedNonIm.auto ?? 0) + (resolvedNonIm.manual ?? 0))).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolvedNonIm.percentage)}</span>
              </td>
              <td className="spec-td" colSpan={3}>
                <div className="spec-chip-row">
                  <button className="spec-chip" onClick={() => openDrilldown('automation.resolved_nstt.non_im')}>
                    Auto: <strong>{cnt(resolvedNonIm.auto)}</strong>
                  </button>
                  <button className="spec-chip" onClick={() => openDrilldown('automation.resolved_nstt.non_im')}>
                    Manual: <strong>{cnt(resolvedNonIm.manual)}</strong>
                  </button>
                </div>
              </td>
            </tr>

            {/* ── Wrong NSTT by Automation (1 row) ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Wrong NSTT Attached by Automation</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('wrong_nstt.automation_ang_txn')}>
                  {cnt(wrong_nstt.automation_ang_txn).toLocaleString()}
                </button>
              </td>
              <TC colSpan={5} cls="spec-na">—</TC>
            </tr>

            {/* ════════════════════════════════════════════════════════
                MANUAL CAPTURED — rows 9..13
                ════════════════════════════════════════════════════════ */}

            {/* Row 9: Manual > Before SR Creation */}
            <tr className="spec-row spec-row-manual-start">
              <TC cls="spec-cell-manual spec-label-bold" rowSpan={5}>Manual Captured</TC>
              <td className="spec-td spec-count spec-cell-manual" rowSpan={5}>
                <button className="spec-count-btn manual" onClick={() => openDrilldown('manual')}>
                  {cnt(manual.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manual.percentage)}</span>
              </td>
              <TC cls="spec-label-med">Manual NSTT Before SR Creation</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('manual.before_sr_creation')}>
                  {cnt(manBefore.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manBefore.percentage)}</span>
              </td>
              <TC colSpan={3} cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.before_sr_creation.sa"
                nsaKey="manual.before_sr_creation.nsa"
                sa={manBefore.sa}
                nsa={manBefore.nsa}
              />
            </tr>

            {/* Row 10: Manual > After SR Creation */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT After SR Creation</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('manual.after_sr_creation')}>
                  {cnt(manAfter.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manAfter.percentage)}</span>
              </td>
              <TC colSpan={3} cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.after_sr_creation.sa"
                nsaKey="manual.after_sr_creation.nsa"
                sa={manAfter.sa}
                nsa={manAfter.nsa}
              />
            </tr>

            {/* Row 11: Manual > Resolved */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT Resolved</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('manual.resolved')}>
                  {cnt(manResolved.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manResolved.percentage)}</span>
              </td>
              <TC colSpan={3} cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.resolved.sa"
                nsaKey="manual.resolved.nsa"
                sa={manResolved.sa}
                nsa={manResolved.nsa}
              />
            </tr>

            {/* Row 12: Wrong NSTT by Engineer */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Wrong NSTT Attached by Engineer</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('wrong_nstt.engineer_ang_txn')}>
                  {cnt(wrong_nstt.engineer_ang_txn).toLocaleString()}
                </button>
              </td>
              <TC colSpan={5} cls="spec-na">—</TC>
            </tr>

          </tbody>
        </table>
      </div>

      {/* ── Manually Tagged section ─────────────────────────── */}
      <div className="spec-manually-tagged">
        <span className="spec-section-label">Manually tagged – NSTT Before SR Creation</span>
        <div className="spec-tag-chips">
          <span className="spec-tag-chip">
            SA: <strong>{cnt(manBefore.sa).toLocaleString()}</strong>
          </span>
          <span className="spec-tag-chip">
            NSA: <strong>{cnt(manBefore.nsa).toLocaleString()}</strong>
          </span>
        </div>
      </div>

    </div>
  )
}
