import React from 'react'
import { useNstt } from '../../context/NsttContext'
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
 * All sub-bifurcation and sub-sub-bifurcation percentages use nstt_count as the base denominator.
 * Headers: dark blue #1F4E78, white bold text, center-aligned, thin borders.
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

  // Percentage and count helpers (all sub-percentages use nstt_count as base)
  const pct  = (v) => (v == null ? '–' : `${v}%`)
  const cnt  = (v) => (v == null ? 0 : v)
  const calcSubPct = (v) => (!nstt_count || nstt_count <= 0 || v == null ? '–' : `${((v / nstt_count) * 100).toFixed(1)}%`)

  /** SA + NSA pair with count and percentage in the same row */
  const SaNsa = ({ saKey, nsaKey, sa, nsa }) => (
    <>
      <td className="spec-td spec-count">
        <button type="button" className="spec-count-btn sa" onClick={() => openDrilldown(saKey)} title={`SA: ${cnt(sa)}`}>
          {cnt(sa).toLocaleString()}
        </button>
        <span className="spec-pct-sub">{calcSubPct(sa)}</span>
      </td>
      <td className="spec-td spec-count">
        <button type="button" className="spec-count-btn nsa" onClick={() => openDrilldown(nsaKey)} title={`NSA: ${cnt(nsa)}`}>
          {cnt(nsa).toLocaleString()}
        </button>
        <span className="spec-pct-sub">{calcSubPct(nsa)}</span>
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
            Eligible SRs (NSTT Count): <strong>{cnt(nstt_count).toLocaleString()}</strong> / {cnt(total_sr).toLocaleString()} ({pct(nstt_percentage)})
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
              <th className="spec-th spec-th-sub">SA NSTT Count (%)</th>
              <th className="spec-th spec-th-sub">NSA NSTT Count (%)</th>
            </tr>
          </thead>

          <tbody>

            {/* ════════════════════════════════════════════════════════
                AUTOMATION CAPTURED — 10 rows (Same: 4, Diff: 1, Res: 4, Wrong: 1)
                ════════════════════════════════════════════════════════ */}

            {/* Row 1: Auto > Same NSTT > IM > Auto */}
            <tr className="spec-row spec-row-auto-start">
              {/* Total SR — spans all 14 rows */}
              <td className="spec-td spec-sticky spec-cell-total" rowSpan={14}>
                <button className="spec-count-btn total" onClick={() => openDrilldown('total_sr')} title="Drilldown: Total SR">
                  {cnt(total_sr).toLocaleString()}
                </button>
              </td>
              {/* NSTT Count */}
              <td className="spec-td spec-sticky spec-cell-nstt" rowSpan={14}>
                <button className="spec-count-btn nstt" onClick={() => openDrilldown('nstt_count')} title="Drilldown: NSTT Count">
                  {cnt(nstt_count).toLocaleString()}
                </button>
              </td>
              {/* Percentage NSTT Count */}
              <td className="spec-td spec-sticky spec-cell-pct" rowSpan={14}>
                {pct(nstt_percentage)}
              </td>

              {/* Sub Bif: Automation Captured (spans 10 automation rows) */}
              <TC cls="spec-cell-auto spec-label-bold" rowSpan={10}>Automation Captured</TC>
              <td className="spec-td spec-count spec-cell-auto" rowSpan={10}>
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

            {/* ── Row 5: Different NSTT ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Auto Capture – Different NSTT</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt')}>
                  {cnt(diff.count).toLocaleString()}
                </button>
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
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.incident_sa_auto_nsa')}>
                      {cnt(diff.incident_sa_auto_nsa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_sa_auto_nsa)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.incident_nsa_auto_sa')}>
                      {cnt(diff.incident_nsa_auto_sa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.incident_nsa_auto_sa)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.both_nsa')}>
                      {cnt(diff.both_nsa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.both_nsa)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.both_sa')}>
                      {cnt(diff.both_sa).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.both_sa)}</span>
                  </div>
                  <div className="spec-subsub-item">
                    <button className="spec-count-btn" onClick={() => openDrilldown('automation.different_nstt.unknown')}>
                      {cnt(diff.unknown).toLocaleString()}
                    </button>
                    <span className="spec-pct-sub">{calcSubPct(diff.unknown)}</span>
                  </div>
                </div>
              </td>
              {/* Detailed Bifurcation: 3 cols */}
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* ── Rows 6..9: Resolved NSTT > IM (Auto / Manual) & Non IM (Auto / Manual) ── */}
            {/* Row 6: Resolved > IM > Auto */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med" rowSpan={4}>Auto Capture – Resolved NSTT</TC>
              <td className="spec-td spec-count" rowSpan={4}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt')}>
                  {cnt(resolved.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolved.percentage)}</span>
              </td>
              <TC rowSpan={2}>IM</TC>
              <td className="spec-td spec-count" rowSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.im')}>
                  {cnt(resolvedIm.count ?? ((resolvedIm.auto ?? 0) + (resolvedIm.manual ?? 0))).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolvedIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <td className="spec-td spec-count" colSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.im.auto')}>
                  {cnt(resolvedIm.auto).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(resolvedIm.auto)}</span>
              </td>
            </tr>

            {/* Row 7: Resolved > IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className="spec-td spec-count" colSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.im.manual')}>
                  {cnt(resolvedIm.manual).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(resolvedIm.manual)}</span>
              </td>
            </tr>

            {/* Row 8: Resolved > Non IM > Auto */}
            <tr className="spec-row">
              <TC rowSpan={2}>Non IM</TC>
              <td className="spec-td spec-count" rowSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.non_im')}>
                  {cnt(resolvedNonIm.count ?? ((resolvedNonIm.auto ?? 0) + (resolvedNonIm.manual ?? 0))).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(resolvedNonIm.percentage)}</span>
              </td>
              <TC>Auto</TC>
              <td className="spec-td spec-count" colSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.non_im.auto')}>
                  {cnt(resolvedNonIm.auto).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(resolvedNonIm.auto)}</span>
              </td>
            </tr>

            {/* Row 9: Resolved > Non IM > Manual */}
            <tr className="spec-row">
              <TC>Manual</TC>
              <td className="spec-td spec-count" colSpan={2}>
                <button className="spec-count-btn" onClick={() => openDrilldown('automation.resolved_nstt.non_im.manual')}>
                  {cnt(resolvedNonIm.manual).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(resolvedNonIm.manual)}</span>
              </td>
            </tr>

            {/* ── Row 10: Wrong NSTT by Automation (1 row) ── */}
            <tr className="spec-row spec-row-subgroup">
              <TC cls="spec-label-med">Wrong NSTT Attached by Automation</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('wrong_nstt.automation_ang_txn')}>
                  {cnt(wrong_nstt.automation_ang_txn).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(wrong_nstt.automation_ang_txn)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
            </tr>

            {/* ════════════════════════════════════════════════════════
                MANUAL CAPTURED — 4 rows (Before: 1, After: 1, Res: 1, Wrong: 1)
                ════════════════════════════════════════════════════════ */}

            {/* Row 11: Manual > Before SR Creation */}
            <tr className="spec-row spec-row-manual-start">
              <TC cls="spec-cell-manual spec-label-bold" rowSpan={4}>Manual Captured</TC>
              <td className="spec-td spec-count spec-cell-manual" rowSpan={4}>
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
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.before_sr_creation.sa"
                nsaKey="manual.before_sr_creation.nsa"
                sa={manBefore.sa}
                nsa={manBefore.nsa}
              />
            </tr>

            {/* Row 12: Manual > After SR Creation */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT After SR Creation</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('manual.after_sr_creation')}>
                  {cnt(manAfter.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manAfter.percentage)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.after_sr_creation.sa"
                nsaKey="manual.after_sr_creation.nsa"
                sa={manAfter.sa}
                nsa={manAfter.nsa}
              />
            </tr>

            {/* Row 13: Manual > Resolved */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Manual NSTT Resolved</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('manual.resolved')}>
                  {cnt(manResolved.count).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{pct(manResolved.percentage)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC cls="spec-na">—</TC>
              <SaNsa
                saKey="manual.resolved.sa"
                nsaKey="manual.resolved.nsa"
                sa={manResolved.sa}
                nsa={manResolved.nsa}
              />
            </tr>

            {/* Row 14: Wrong NSTT by Engineer */}
            <tr className="spec-row">
              <TC cls="spec-label-med">Wrong NSTT Attached by Engineer</TC>
              <td className="spec-td spec-count">
                <button className="spec-count-btn" onClick={() => openDrilldown('wrong_nstt.engineer_ang_txn')}>
                  {cnt(wrong_nstt.engineer_ang_txn).toLocaleString()}
                </button>
                <span className="spec-pct-sub">{calcSubPct(wrong_nstt.engineer_ang_txn)}</span>
              </td>
              <TC colSpan={2} cls="spec-na">—</TC>
              <TC colSpan={3} cls="spec-na">—</TC>
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

