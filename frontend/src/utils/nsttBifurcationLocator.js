/**
 * nsttBifurcationLocator.js
 *
 * Provides extraction, classification, and live lookup helpers to locate any
 * record (by Incident ID or SR Number) within the NSTT Hierarchical Matrix.
 * Identifies the exact leaf bifurcation node, row identifier, breadcrumbs,
 * and drilldown keys so the matching table cells can blink.
 */

/**
 * Extracts and normalizes the Incident ID from any record representation.
 */
export function extractIncidentId(r) {
  if (!r) return ''
  const val =
    r.INCIDENTID ??
    r.INCIDENT_ID ??
    r['INCIDENT ID'] ??
    r.IncidentID ??
    r.incident_id ??
    r.INCIDENT_NUMBER ??
    r['Incident Number'] ??
    r.incident_number ??
    r.AUTOMATION_UPDATE_NSTT_NUMBER ??
    r['AUTOMATION UPDATE NSTT NUMBER'] ??
    r.automation_update_nstt_number ??
    ''
  return String(val).trim()
}

/**
 * Extracts and normalizes the SR Number from any record representation.
 */
export function extractSrNumber(r) {
  if (!r) return ''
  const val =
    r.SRNUMBER ??
    r.SR_NUMBER ??
    r['SR NUMBER'] ??
    r.SRNO ??
    r.SR_NO ??
    r['SR NO'] ??
    r['Sr Number'] ??
    r.sr_number ??
    ''
  return String(val).trim()
}

/**
 * Classifies a single record into its leaf bifurcation key, rowKey, and descriptive breadcrumbs.
 * Exactly aligns with backend predicates in aggregator.py and rows in NsttSummaryTable.jsx.
 */
export function classifyRecordBifurcation(r) {
  if (!r) return null

  // 1. Wrong NSTT Exceptions
  const exceptionType = r.exception_type ?? r.EXCEPTION_TYPE
  if (exceptionType) {
    const excStr = String(exceptionType).toLowerCase()
    if (excStr.includes('automation') || excStr.includes('auto')) {
      return {
        key: 'wrong_nstt.automation_ang_txn',
        rowKey: 'row_wrong_auto',
        breadcrumbs: ['Automation Captured', 'Wrong NSTT Attached by Automation Ang in TXN Attribution'],
        label: 'Wrong NSTT (Automation)',
      }
    }
    if (excStr.includes('engineer') || excStr.includes('eng')) {
      return {
        key: 'wrong_nstt.engineer_ang_txn',
        rowKey: 'row_wrong_eng',
        breadcrumbs: ['Manual Captured', 'Wrong NSTT Attached by Engineer Ang in TXN Attribution'],
        label: 'Wrong NSTT (Engineer)',
      }
    }
  }

  // 2. Failures
  const failureCategory = r.failure_category ?? r.FAILURE_CATEGORY
  if (failureCategory) {
    const fc = String(failureCategory).toLowerCase()
    if (fc.includes('not found')) {
      return {
        key: 'failures.nstt_not_found',
        rowKey: 'row_failures_nstt_not_found',
        breadcrumbs: ['Failures', 'NSTT Number not found in Remedy'],
        label: 'NSTT Number not found in Remedy',
      }
    }
    if (fc.includes('ring')) {
      return {
        key: 'failures.ring_failure',
        rowKey: 'row_manual_before',
        breadcrumbs: ['Failure Analysis', 'Ring Failure'],
        label: 'Ring Failure',
      }
    }
    if (fc.includes('section')) {
      return {
        key: 'failures.section_failure',
        rowKey: 'row_manual_before',
        breadcrumbs: ['Failure Analysis', 'Section Failure'],
        label: 'Section Failure',
      }
    }
    if (fc.includes('unstitched')) {
      return {
        key: 'failures.unstitched',
        rowKey: 'row_manual_before',
        breadcrumbs: ['Failure Analysis', 'Unstitched'],
        label: 'Unstitched',
      }
    }
    if (fc.includes('other')) {
      return {
        key: 'failures.others',
        rowKey: 'row_manual_before',
        breadcrumbs: ['Failure Analysis', 'Others'],
        label: 'Others',
      }
    }
  }

  // 3. Non-NSTT check (Total SR)
  // If is_nstt is explicitly false, or if INCIDENTID is blank
  const hasIncident = Boolean(extractIncidentId(r))
  const isNstt = r.is_nstt !== undefined ? Boolean(r.is_nstt) : hasIncident
  if (!isNstt) {
    return {
      key: 'total_sr',
      rowKey: 'row_total_sr',
      breadcrumbs: ['Total SR (Non-NSTT: Blank Incident ID)'],
      label: 'Total SR (Non-NSTT)',
    }
  }

  // 4. Capture Type: Automation vs Manual
  const captureType = (r.capture_type ?? r.CAPTURE_TYPE ?? '').trim()
  const isAuto =
    captureType.toLowerCase() === 'automation' ||
    Boolean(r.AUTOMATION_UPDATE_NSTT_NUMBER && String(r.AUTOMATION_UPDATE_NSTT_NUMBER).trim())

  if (isAuto) {
    const nsttType = (r.nstt_type ?? r.NSTT_TYPE ?? '').trim()

    // 4a. Same NSTT
    if (nsttType === 'Same NSTT' || (!nsttType && r.AUTOMATION_UPDATE_NSTT_NUMBER === extractIncidentId(r))) {
      const isNonIm =
        r.factory_type === 'Non IM' ||
        r.FACTORY === 'Non IM' ||
        String(r.FACTORY || '').toLowerCase().includes('non im')
      const factory = isNonIm ? 'non_im' : 'im'
      const factoryLabel = isNonIm ? 'Non IM' : 'IM'

      const isManualAlloc =
        (r.allocation_type || r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'manual' ||
        (r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'no'
      const alloc = isManualAlloc ? 'manual' : 'auto'
      const allocLabel = isManualAlloc ? 'Manual' : 'Auto'

      const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
      let impact = 'unknown'
      let impactLabel = 'Impact Unknown'
      if (impactRaw === 'SA') {
        impact = 'sa'
        impactLabel = 'SA NSTT'
      } else if (impactRaw === 'NSA') {
        impact = 'nsa'
        impactLabel = 'NSA NSTT'
      }

      return {
        key: `automation.same_nstt.${factory}.${alloc}.${impact}`,
        rowKey: `row_same_${factory}_${alloc}`,
        breadcrumbs: ['Automation Captured', 'Auto Capture – Same NSTT', factoryLabel, allocLabel, impactLabel],
        label: `Same NSTT ➔ ${factoryLabel} ➔ ${allocLabel} ➔ ${impactLabel}`,
      }
    }

    // 4b. Different NSTT
    if (nsttType === 'Different NSTT' || (!nsttType && r.AUTOMATION_UPDATE_NSTT_NUMBER && r.AUTOMATION_UPDATE_NSTT_NUMBER !== extractIncidentId(r))) {
      const diffCat = r.diff_nstt_category || r.DIFF_NSTT_CATEGORY || ''
      let subKey = 'unknown'
      let diffLabel = 'Impact Unknown / Not Found in Remedy'

      if (diffCat === 'Incident SA auto NSA' || diffCat.includes('SA auto NSA')) {
        subKey = 'incident_sa_auto_nsa'
        diffLabel = 'Incident SA auto NSA'
      } else if (diffCat === 'Incident NSA auto SA' || diffCat.includes('NSA auto SA')) {
        subKey = 'incident_nsa_auto_sa'
        diffLabel = 'Incident NSA auto SA'
      } else if (diffCat === 'Both NSA' || diffCat.includes('Both NSA')) {
        subKey = 'both_nsa'
        diffLabel = 'Both NSA'
      } else if (diffCat === 'Both SA' || diffCat.includes('Both SA')) {
        subKey = 'both_sa'
        diffLabel = 'Both SA'
      }

      return {
        key: `automation.different_nstt.${subKey}`,
        rowKey: 'row_diff_nstt',
        breadcrumbs: ['Automation Captured', 'Auto Capture – Different NSTT', diffLabel],
        label: `Different NSTT ➔ ${diffLabel}`,
      }
    }

    // 4c. Resolved NSTT
    if (nsttType === 'Resolved NSTT') {
      const isNonIm =
        r.factory_type === 'Non IM' ||
        r.FACTORY === 'Non IM' ||
        String(r.FACTORY || '').toLowerCase().includes('non im')
      const factory = isNonIm ? 'non_im' : 'im'
      const factoryLabel = isNonIm ? 'Non IM' : 'IM'

      const isManualAlloc =
        (r.allocation_type || r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'manual' ||
        (r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'no'
      const alloc = isManualAlloc ? 'manual' : 'auto'
      const allocLabel = isManualAlloc ? 'Manual' : 'Auto'

      const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
      let impact = 'unknown'
      let impactLabel = 'Impact Unknown'
      if (impactRaw === 'SA') {
        impact = 'sa'
        impactLabel = 'SA NSTT'
      } else if (impactRaw === 'NSA') {
        impact = 'nsa'
        impactLabel = 'NSA NSTT'
      }

      return {
        key: `automation.resolved_nstt.${factory}.${alloc}.${impact}`,
        rowKey: `row_resolved_${factory}_${alloc}`,
        breadcrumbs: ['Automation Captured', 'Auto Capture – Resolved NSTT', factoryLabel, allocLabel, impactLabel],
        label: `Resolved NSTT ➔ ${factoryLabel} ➔ ${allocLabel} ➔ ${impactLabel}`,
      }
    }
  }

  // 5. Manual Captured
  const timing = (r.timing_type || r.TIMING_TYPE || '').toString().trim()
  let timingKey = 'before_sr_creation'
  let timingLabel = 'Manual NSTT Before SR Creation'

  if (timing.toLowerCase().includes('after')) {
    timingKey = 'after_sr_creation'
    timingLabel = 'Manual NSTT After SR Creation'
  } else if (timing.toLowerCase().includes('resolved')) {
    timingKey = 'resolved'
    timingLabel = 'Manual NSTT Resolved'
  }

  const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
  let impact = 'unknown'
  let impactLabel = 'Impact Unknown'
  if (impactRaw === 'SA') {
    impact = 'sa'
    impactLabel = 'SA NSTT'
  } else if (impactRaw === 'NSA') {
    impact = 'nsa'
    impactLabel = 'NSA NSTT'
  }

  const result = {
    key: `manual.${timingKey}.${impact}`,
    rowKey: `row_manual_${timingKey}`,
    breadcrumbs: ['Manual Captured', timingLabel, impactLabel],
    label: `Manual Captured ➔ ${timingLabel} ➔ ${impactLabel}`,
  }

  // If this manual before record also maps to failure category, link failure key
  if (r.failure_category) {
    const fc = String(r.failure_category).toLowerCase()
    if (fc.includes('ring')) result.secondaryKey = 'failures.ring_failure'
    else if (fc.includes('section')) result.secondaryKey = 'failures.section_failure'
    else if (fc.includes('unstitched')) result.secondaryKey = 'failures.unstitched'
    else if (fc.includes('other')) result.secondaryKey = 'failures.others'
  }

  return result
}

/**
 * Returns ALL hierarchical drill-down keys where a record is present.
 * Covers every drilldown button from top-level down to leaf:
 * e.g. total_sr, nstt_count, automation, automation.same_nstt, automation.same_nstt.im,
 *      automation.same_nstt.im.auto, and automation.same_nstt.im.auto.sa.
 */
export function getAllDrilldownKeysForRecord(r) {
  if (!r) return []
  const keys = new Set()

  // 1. Total SR
  if (r.is_total_sr || r.is_total_sr === undefined) {
    keys.add('total_sr')
  }

  // 2. NSTT Count
  const hasIncident = Boolean(extractIncidentId(r))
  const isNstt = r.is_nstt !== undefined ? Boolean(r.is_nstt) : hasIncident
  if (isNstt) {
    keys.add('nstt_count')
    keys.add('nstt')
  } else {
    // Non-NSTT total SR record
    return Array.from(keys)
  }

  // 3. Exception (Wrong NSTT)
  const exceptionType = r.exception_type ?? r.EXCEPTION_TYPE
  if (exceptionType) {
    const excStr = String(exceptionType).toLowerCase()
    if (excStr.includes('automation') || excStr.includes('auto')) {
      keys.add('automation')
      keys.add('wrong_nstt')
      keys.add('wrong_nstt.automation_ang_txn')
      return Array.from(keys)
    }
    if (excStr.includes('engineer') || excStr.includes('eng')) {
      keys.add('manual')
      keys.add('wrong_nstt')
      keys.add('wrong_nstt.engineer_ang_txn')
      return Array.from(keys)
    }
  }

  // 4. Failures (NSTT Not Found in Remedy)
  const failureCategory = r.failure_category ?? r.FAILURE_CATEGORY
  if (failureCategory) {
    const fc = String(failureCategory).toLowerCase()
    if (fc.includes('not found')) {
      keys.add('failures')
      keys.add('failures.nstt_not_found')
      return Array.from(keys)
    }
  }

  // 5. Capture Type: Automation vs Manual
  const captureType = (r.capture_type ?? r.CAPTURE_TYPE ?? '').trim()
  const isAuto =
    captureType.toLowerCase() === 'automation' ||
    Boolean(r.AUTOMATION_UPDATE_NSTT_NUMBER && String(r.AUTOMATION_UPDATE_NSTT_NUMBER).trim())

  if (isAuto) {
    keys.add('automation')
    const nsttType = (r.nstt_type ?? r.NSTT_TYPE ?? '').trim()

    // 5a. Same NSTT
    if (nsttType === 'Same NSTT' || (!nsttType && r.AUTOMATION_UPDATE_NSTT_NUMBER === extractIncidentId(r))) {
      keys.add('automation.same_nstt')
      keys.add('same_nstt')

      const isNonIm =
        r.factory_type === 'Non IM' ||
        r.FACTORY === 'Non IM' ||
        String(r.FACTORY || '').toLowerCase().includes('non im')
      const factory = isNonIm ? 'non_im' : 'im'
      keys.add(`automation.same_nstt.${factory}`)

      const isManualAlloc =
        (r.allocation_type || r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'manual' ||
        (r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'no'
      const alloc = isManualAlloc ? 'manual' : 'auto'
      keys.add(`automation.same_nstt.${factory}.${alloc}`)

      const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
      let impact = 'unknown'
      if (impactRaw === 'SA') impact = 'sa'
      else if (impactRaw === 'NSA') impact = 'nsa'
      keys.add(`automation.same_nstt.${factory}.${alloc}.${impact}`)

      return Array.from(keys)
    }

    // 5b. Different NSTT
    if (nsttType === 'Different NSTT' || (!nsttType && r.AUTOMATION_UPDATE_NSTT_NUMBER && r.AUTOMATION_UPDATE_NSTT_NUMBER !== extractIncidentId(r))) {
      keys.add('automation.different_nstt')
      keys.add('different_nstt')

      const diffCat = r.diff_nstt_category || r.DIFF_NSTT_CATEGORY || ''
      let subKey = 'unknown'
      if (diffCat === 'Incident SA auto NSA' || diffCat.includes('SA auto NSA')) {
        subKey = 'incident_sa_auto_nsa'
      } else if (diffCat === 'Incident NSA auto SA' || diffCat.includes('NSA auto SA')) {
        subKey = 'incident_nsa_auto_sa'
      } else if (diffCat === 'Both NSA' || diffCat.includes('Both NSA')) {
        subKey = 'both_nsa'
      } else if (diffCat === 'Both SA' || diffCat.includes('Both SA')) {
        subKey = 'both_sa'
      }
      keys.add(`automation.different_nstt.${subKey}`)

      return Array.from(keys)
    }

    // 5c. Resolved NSTT
    if (nsttType === 'Resolved NSTT') {
      keys.add('automation.resolved_nstt')
      keys.add('resolved_nstt')

      const isNonIm =
        r.factory_type === 'Non IM' ||
        r.FACTORY === 'Non IM' ||
        String(r.FACTORY || '').toLowerCase().includes('non im')
      const factory = isNonIm ? 'non_im' : 'im'
      keys.add(`automation.resolved_nstt.${factory}`)

      const isManualAlloc =
        (r.allocation_type || r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'manual' ||
        (r.AUTO_ALLOCATION || '').toString().toLowerCase() === 'no'
      const alloc = isManualAlloc ? 'manual' : 'auto'
      keys.add(`automation.resolved_nstt.${factory}.${alloc}`)

      const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
      let impact = 'unknown'
      if (impactRaw === 'SA') impact = 'sa'
      else if (impactRaw === 'NSA') impact = 'nsa'
      keys.add(`automation.resolved_nstt.${factory}.${alloc}.${impact}`)

      return Array.from(keys)
    }
  }

  // 6. Manual Captured
  keys.add('manual')
  const timing = (r.timing_type || r.TIMING_TYPE || '').toString().trim()
  let timingKey = 'before_sr_creation'

  if (timing.toLowerCase().includes('after')) {
    timingKey = 'after_sr_creation'
  } else if (timing.toLowerCase().includes('resolved')) {
    timingKey = 'resolved'
  }
  keys.add(`manual.${timingKey}`)

  const impactRaw = (r.impact_type || r.INCIDENT_IMPACT || '').toString().toUpperCase().trim()
  let impact = 'unknown'
  if (impactRaw === 'SA') impact = 'sa'
  else if (impactRaw === 'NSA') impact = 'nsa'
  keys.add(`manual.${timingKey}.${impact}`)

  // Failure categories for manual records
  if (failureCategory) {
    const fc = String(failureCategory).toLowerCase()
    keys.add('failures')
    keys.add('failures.grand_total')
    if (fc.includes('ring')) keys.add('failures.ring_failure')
    else if (fc.includes('section')) keys.add('failures.section_failure')
    else if (fc.includes('unstitched')) keys.add('failures.unstitched')
    else if (fc.includes('other')) keys.add('failures.others')
  }

  return Array.from(keys)
}

/**
 * Searches records for matching Incident ID or SR Number and groups them by bifurcation.
 *
 * @param {Array<Object>} records - Raw records from classifiedMasterResponse or masterResponse.
 * @param {string} rawQuery - Search string typed by user.
 * @returns {Object} Search result containing matched count, bifurcations list, and all drilldown keys to highlight.
 */
export function findBifurcationsForQuery(records, rawQuery) {
  if (!Array.isArray(records) || records.length === 0) {
    return {
      query: rawQuery,
      totalMatches: 0,
      bifurcations: [],
      allKeys: [],
      allRowKeys: [],
      matchedRecords: [],
    }
  }

  const q = String(rawQuery || '').trim().toUpperCase()
  if (!q) {
    return {
      query: rawQuery,
      totalMatches: 0,
      bifurcations: [],
      allKeys: [],
      allRowKeys: [],
      matchedRecords: [],
    }
  }

  // 1. Separate exact matches vs partial matches
  const exactMatches = []
  const partialMatches = []

  for (const r of records) {
    const incId = extractIncidentId(r).toUpperCase()
    const srNo = extractSrNumber(r).toUpperCase()
    const autoNo = String(r.AUTOMATION_UPDATE_NSTT_NUMBER || '').trim().toUpperCase()

    if (incId === q || srNo === q || autoNo === q) {
      exactMatches.push(r)
    } else if (
      (incId && incId.includes(q)) ||
      (srNo && srNo.includes(q)) ||
      (autoNo && autoNo.includes(q))
    ) {
      partialMatches.push(r)
    }
  }

  // If we have exact matches, prioritize them; otherwise show partial matches
  const matchedRecords = exactMatches.length > 0 ? exactMatches : partialMatches
  if (matchedRecords.length === 0) {
    return {
      query: rawQuery,
      totalMatches: 0,
      bifurcations: [],
      allKeys: [],
      allRowKeys: [],
      matchedRecords: [],
    }
  }

  const bifurcationsMap = new Map()
  const allKeysSet = new Set()
  const allRowKeysSet = new Set()

  for (const r of matchedRecords) {
    const info = classifyRecordBifurcation(r)
    if (!info) continue

    // Add ALL hierarchical drilldown categories where this record is present!
    const allDrilldowns = getAllDrilldownKeysForRecord(r)
    for (const k of allDrilldowns) {
      allKeysSet.add(k)
    }

    if (info.key) allKeysSet.add(info.key)
    if (info.secondaryKey) allKeysSet.add(info.secondaryKey)
    if (info.rowKey) allRowKeysSet.add(info.rowKey)

    if (!bifurcationsMap.has(info.key)) {
      bifurcationsMap.set(info.key, {
        key: info.key,
        secondaryKey: info.secondaryKey,
        rowKey: info.rowKey,
        breadcrumbs: info.breadcrumbs,
        label: info.label,
        records: [r],
      })
    } else {
      bifurcationsMap.get(info.key).records.push(r)
    }
  }

  return {
    query: rawQuery,
    totalMatches: matchedRecords.length,
    bifurcations: Array.from(bifurcationsMap.values()),
    allKeys: Array.from(allKeysSet),
    allRowKeys: Array.from(allRowKeysSet),
    matchedRecords,
  }
}
