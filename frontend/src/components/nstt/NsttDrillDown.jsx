import { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import { useNstt } from '../../context/NsttContext'
import ExcelFilterDropdown from './ExcelFilterDropdown'
import './NsttDrillDown.css'

/**
 * Normalizes and extracts the column value for a record.
 */
function getRecordValue(r, colId) {
  if (!r) return ''
  switch (colId) {
    case 'INCIDENTID': {
      const v =
        r.INCIDENTID ??
        r.INCIDENT_ID ??
        r['INCIDENT ID'] ??
        r.IncidentID ??
        r.incident_id ??
        r.INCIDENT_NUMBER ??
        r['Incident Number'] ??
        r.incident_number ??
        ''
      return String(v).trim()
    }
    case 'SR_NUMBER': {
      const v =
        r.SRNUMBER ??
        r.SR_NUMBER ??
        r['SR NUMBER'] ??
        r.SRNO ??
        r['SR NO'] ??
        r['Sr Number'] ??
        r.sr_number ??
        ''
      return String(v).trim()
    }
    case 'AUTOMATION_UPDATE_NSTT_NUMBER': {
      const v =
        r.AUTOMATION_UPDATE_NSTT_NUMBER ??
        r['AUTOMATION UPDATE NSTT NUMBER'] ??
        r.automation_update_nstt_number ??
        ''
      return String(v).trim()
    }
    case 'ATTRIBUTEDTO': {
      const v =
        r.ATTRIBUTEDTO ??
        r['ATTRIBUTED TO'] ??
        r.AttributedTo ??
        r.attributed_to ??
        ''
      return String(v).trim()
    }
    case 'FACTORY': {
      const v = r.FACTORY ?? r.Factory ?? r.factory ?? ''
      return String(v).trim()
    }
    case 'AUTO_ALLOCATION': {
      const v =
        r.AUTO_ALLOCATION ??
        r['AUTO ALLOCATION'] ??
        r.auto_allocation ??
        ''
      return String(v).trim()
    }
    case 'INCIDENT_IMPACT': {
      let incImp =
        r.INCIDENT_IMPACT ??
        r['INCIDENT IMPACT'] ??
        r.incident_impact
      const diffCat = r.diff_nstt_category || ''
      if (!incImp && diffCat) {
        if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both SA') incImp = 'SA'
        else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both NSA') incImp = 'NSA'
        else if (diffCat === 'Impact Unknown / Not Found in Remedy') incImp = 'Unknown'
      }
      return String(incImp ?? '').trim()
    }
    case 'AUTOMATION_IMPACT': {
      let autoImp =
        r.AUTOMATION_IMPACT ??
        r['AUTOMATION IMPACT'] ??
        r.automation_impact
      const diffCat = r.diff_nstt_category || ''
      if (!autoImp && diffCat) {
        if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both NSA') autoImp = 'NSA'
        else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both SA') autoImp = 'SA'
        else if (
          diffCat === 'Impact Unknown / Not Found in Remedy' ||
          r.nstt_type === 'Different NSTT'
        )
          autoImp = 'Unknown'
      }
      return String(autoImp ?? '').trim()
    }
    case 'SRCREATIONTIME': {
      const v =
        r.SRCREATIONTIME ??
        r['SR CREATION TIME'] ??
        r.srcreationtime ??
        r.SR_CREATION_TIME ??
        ''
      return String(v).trim()
    }
    case 'UP_TIME': {
      const v =
        r.UP_TIME ??
        r['UP TIME'] ??
        r.up_time ??
        ''
      return String(v).trim()
    }
    case 'Submit Date': {
      const v =
        r['Submit Date'] ??
        r.SUBMIT_DATE ??
        r.submit_date ??
        r['SubmitDate'] ??
        ''
      return String(v).trim()
    }
    case 'DESCRIPTION': {
      const v =
        r.DESCRIPTION ??
        r.Description ??
        r.description ??
        ''
      return String(v).trim()
    }
    case 'AUTOMATION_RCA_CONCLUSION_TEXT': {
      const v =
        r.AUTOMATION_RCA_CONCLUSION_TEXT ??
        r['AUTOMATION RCA CONCLUSION TEXT'] ??
        r.AUTOMATION_RCA_CONCLUSION ??
        r['AUTOMATION_RCA_CONCLUSION'] ??
        r.automation_rca_conclusion_text ??
        r.rca_conclusion_text ??
        ''
      return String(v).trim()
    }
    default:
      return String(r[colId] ?? '').trim()
  }
}

const toDisplayVal = (val) => (!val || val === '—' ? '(Blanks)' : val)

function FilterIcon({ isFiltered }) {
  if (isFiltered) {
    return (
      <svg
        width="11"
        height="11"
        viewBox="0 0 16 16"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .38.82L9.5 7.7V13.5a.5.5 0 0 1-.76.42l-2-1.25A.5.5 0 0 1 6.5 12.25V7.7L1.62 1.82A.5.5 0 0 1 1.5 1.5z" />
      </svg>
    )
  }
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M1.5 2.5a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 .39.812l-4.89 5.868v4.82a.5.5 0 0 1-.74.436l-2-1.143A.5.5 0 0 1 6.5 11.45V8.68L1.61 2.812A.5.5 0 0 1 1.5 2.5z" />
    </svg>
  )
}

/**
 * Safely parses comma/semicolon/whitespace separated ID tokens into an array of strings.
 */
function parseIdTokens(val) {
  if (!val || val === '—') return []
  const raw = String(val).trim()
  if (!raw) return []
  return raw
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/**
 * MultiIdCell - Formats single or multiple comma/space separated IDs.
 * Places 3 to 4 IDs per row (chunked into 4), wrapping remaining IDs onto the next line.
 */
function MultiIdCell({ value, searchQuery }) {
  if (!value || value === '—') {
    return <span>—</span>
  }

  const rawStr = String(value).trim()
  if (!rawStr) {
    return <span>—</span>
  }

  const tokens = parseIdTokens(rawStr)

  if (tokens.length === 0) {
    return <span>—</span>
  }

  const q = searchQuery && searchQuery.trim() ? searchQuery.trim().toUpperCase() : null

  if (tokens.length === 1) {
    const isMatched = q && tokens[0].toUpperCase() === q
    return (
      <span
        title={rawStr}
        className={`multi-id-single ${isMatched ? 'multi-id-matched' : ''}`}
      >
        {tokens[0]}
      </span>
    )
  }

  // Chunk IDs into lines of up to 4 (e.g. 7 IDs -> Line 1: 4 IDs, Line 2: 3 IDs)
  const chunks = []
  for (let i = 0; i < tokens.length; i += 4) {
    chunks.push(tokens.slice(i, i + 4))
  }

  return (
    <div className="multi-id-cell" title={rawStr}>
      {chunks.map((chunk, cIdx) => (
        <div key={cIdx} className="multi-id-row">
          {chunk.map((id, idIdx) => {
            const isMatched = q && id.toUpperCase() === q
            const isLastInChunk = idIdx === chunk.length - 1
            const isLastOverall = cIdx === chunks.length - 1 && isLastInChunk

            return (
              <span key={idIdx} className="multi-id-item">
                <span className={`multi-id-token ${isMatched ? 'multi-id-matched' : ''}`}>
                  {id}
                </span>
                {!isLastOverall && <span className="multi-id-comma">,</span>}
              </span>
            )
          })}
        </div>
      ))}
    </div>
  )
}

export default function NsttDrillDown() {
  const {
    isDrilldownOpen,
    isDrilldownLoading,
    drilldownCategory,
    drilldownData,
    closeDrilldown,
    bifurcationQuery,
    setBifurcationQuery,
  } = useNstt()

  const tableWrapperRef = useRef(null)
  const hasAutoScrolledRef = useRef(false)

  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // Column-wise filters: { [colId]: Set<string> }
  const [columnFilters, setColumnFilters] = useState({})
  // Sorting: { colId: string, direction: 'asc' | 'desc' } | null
  const [sortConfig, setSortConfig] = useState(null)
  // Track open filter dropdown by column id
  const [openDropdownCol, setOpenDropdownCol] = useState(null)

  // Check if a record matches the searched Incident ID / SR Number / Automation NSTT Number exactly
  const isRecordMatchingSearch = useCallback((r) => {
    const q = String(bifurcationQuery || '').trim().toUpperCase()
    if (!q) return false
    const incId = getRecordValue(r, 'INCIDENTID').toUpperCase()
    const srNo = getRecordValue(r, 'SR_NUMBER').toUpperCase()
    const autoVal = getRecordValue(r, 'AUTOMATION_UPDATE_NSTT_NUMBER')
    const autoTokens = parseIdTokens(autoVal).map((t) => t.toUpperCase())
    return incId === q || srNo === q || autoTokens.includes(q)
  }, [bifurcationQuery])

  // Reset pagination, filters, and sorting on category change
  useEffect(() => {
    setCurrentPage(1)
    setColumnFilters({})
    setSortConfig(null)
    setOpenDropdownCol(null)
    hasAutoScrolledRef.current = false
    if (tableWrapperRef.current) {
      tableWrapperRef.current.scrollTop = 0
    }
  }, [drilldownCategory])

  // Reset auto-scroll flag when drilldown drawer closes
  useEffect(() => {
    if (!isDrilldownOpen) {
      hasAutoScrolledRef.current = false
    }
  }, [isDrilldownOpen])

  // ESC key to close modal drawer when no dropdown is open
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isDrilldownOpen && !openDropdownCol) {
        closeDrilldown()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isDrilldownOpen, openDropdownCol, closeDrilldown])

  // Auto-scroll to highlighted record row inside drilldown table ONCE on initial open
  useEffect(() => {
    if (
      isDrilldownOpen &&
      bifurcationQuery &&
      !isDrilldownLoading &&
      !hasAutoScrolledRef.current
    ) {
      const timer = setTimeout(() => {
        const highlightedRow = tableWrapperRef.current?.querySelector(
          '.drilldown-row-highlighted'
        )
        if (highlightedRow) {
          highlightedRow.scrollIntoView({ behavior: 'smooth', block: 'center' })
          hasAutoScrolledRef.current = true
        }
      }, 200)
      return () => clearTimeout(timer)
    }
  }, [isDrilldownOpen, bifurcationQuery, isDrilldownLoading])

  // Lock background window scroll when drilldown drawer is open
  useEffect(() => {
    if (isDrilldownOpen) {
      const originalOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = originalOverflow
      }
    }
  }, [isDrilldownOpen])

  const records = useMemo(() => {
    return Array.isArray(drilldownData?.records) ? drilldownData.records : []
  }, [drilldownData])

  // Only display AUTOMATION_IMPACT for the 5 Different NSTT categories
  const isDifferentNsttCategory = useMemo(() => {
    const cat = String(drilldownCategory || '').toLowerCase()
    if (cat.includes('different_nstt') || cat.includes('diff_nstt')) return true
    if (records.length > 0 && records.every((r) => Boolean(r.diff_nstt_category))) return true
    return false
  }, [drilldownCategory, records])

  // Detect if current drilldown is part of the Manual Captured section
  const isManualCaptured = useMemo(() => {
    const cat = String(drilldownCategory || '').toLowerCase()
    if (cat === 'manual' || cat.startsWith('manual.') || cat.includes('engineer')) {
      return true
    }
    if (records.length > 0 && records.every((r) => r.capture_type === 'Manual')) {
      return true
    }
    return false
  }, [drilldownCategory, records])

  // Detect if current drilldown is for Unstitched or failure category containing Unstitched
  const isUnstitchedCategory = useMemo(() => {
    const cat = String(drilldownCategory || '').toLowerCase()
    if (cat.includes('unstitched')) return true
    if (
      records.length > 0 &&
      records.some((r) => {
        const fc = String(r.failure_category || '').toLowerCase()
        if (fc.includes('unstitched')) return true
        const rca = String(
          r.AUTOMATION_RCA_CONCLUSION_TEXT ??
          r['AUTOMATION RCA CONCLUSION TEXT'] ??
          r.AUTOMATION_RCA_CONCLUSION ??
          r.automation_rca_conclusion_text ??
          ''
        ).toLowerCase()
        return rca.includes('unstitched')
      })
    ) {
      return true
    }
    return false
  }, [drilldownCategory, records])

  // Define columns structure dynamically
  const columns = useMemo(() => {
    const cols = [
      {
        id: 'INCIDENTID',
        label: 'INCIDENTID',
        headerClass: 'sticky-col-2 col-incident-id',
        tdClass: 'sticky-col-2 col-incident-id font-mono font-bold',
        render: (r) => (
          <MultiIdCell
            value={getRecordValue(r, 'INCIDENTID')}
            searchQuery={bifurcationQuery}
          />
        ),
      },
      {
        id: 'SR_NUMBER',
        label: 'SR NUMBER',
        headerClass: 'col-sr-number',
        tdClass: 'col-sr-number font-mono',
        render: (r) => (
          <MultiIdCell
            value={getRecordValue(r, 'SR_NUMBER')}
            searchQuery={bifurcationQuery}
          />
        ),
      },
    ]

    if (!isManualCaptured) {
      cols.push({
        id: 'AUTOMATION_UPDATE_NSTT_NUMBER',
        label: 'AUTOMATION UPDATE NSTT NUMBER',
        headerClass: 'col-automation-nstt',
        tdClass: 'col-automation-nstt font-mono text-sm',
        render: (r) => (
          <MultiIdCell
            value={getRecordValue(r, 'AUTOMATION_UPDATE_NSTT_NUMBER')}
            searchQuery={bifurcationQuery}
          />
        ),
      })
    }

    cols.push(
      {
        id: 'ATTRIBUTEDTO',
        label: 'ATTRIBUTEDTO',
        headerClass: 'col-attributed-to',
        tdClass: 'col-attributed-to',
        render: (r) => r.ATTRIBUTEDTO || '—',
      },
      {
        id: 'FACTORY',
        label: 'FACTORY',
        headerClass: 'col-factory',
        tdClass: 'col-factory',
        render: (r) =>
          r.FACTORY ? (
            <span className={`pill-factory ${r.FACTORY === 'IM' ? 'im' : 'non-im'}`}>
              {r.FACTORY}
            </span>
          ) : (
            '—'
          ),
      },
      {
        id: 'AUTO_ALLOCATION',
        label: 'AUTO_ALLOCATION',
        headerClass: 'col-auto-alloc',
        tdClass: 'col-auto-alloc',
        render: (r) => r.AUTO_ALLOCATION || '—',
      },
      {
        id: 'INCIDENT_IMPACT',
        label: 'INCIDENT_IMPACT',
        headerClass: 'col-impact',
        tdClass: 'col-impact',
        render: (r) => {
          let incImp = r.INCIDENT_IMPACT
          const diffCat = r.diff_nstt_category || ''
          if (!incImp && diffCat) {
            if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both SA') incImp = 'SA'
            else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both NSA') incImp = 'NSA'
            else if (diffCat === 'Impact Unknown / Not Found in Remedy') incImp = 'Unknown'
          }
          return incImp ? (
            <span
              className={`pill-impact ${incImp === 'SA' ? 'sa' : incImp === 'NSA' ? 'nsa' : 'unknown'
                }`}
            >
              {incImp}
            </span>
          ) : (
            '—'
          )
        },
      }
    )

    if (isDifferentNsttCategory) {
      cols.push({
        id: 'AUTOMATION_IMPACT',
        label: 'AUTOMATION_IMPACT',
        headerClass: 'col-impact',
        tdClass: 'col-impact',
        render: (r) => {
          let autoImp = r.AUTOMATION_IMPACT
          const diffCat = r.diff_nstt_category || ''
          if (!autoImp && diffCat) {
            if (diffCat === 'Incident SA auto NSA' || diffCat === 'Both NSA') autoImp = 'NSA'
            else if (diffCat === 'Incident NSA auto SA' || diffCat === 'Both SA') autoImp = 'SA'
            else if (
              diffCat === 'Impact Unknown / Not Found in Remedy' ||
              r.nstt_type === 'Different NSTT'
            )
              autoImp = 'Unknown'
          }
          return autoImp ? (
            <span
              className={`pill-impact ${autoImp === 'SA' ? 'sa' : autoImp === 'NSA' ? 'nsa' : 'unknown'
                }`}
            >
              {autoImp}
            </span>
          ) : (
            '—'
          )
        },
      })
    }

    cols.push(
      {
        id: 'SRCREATIONTIME',
        label: 'SRCREATIONTIME',
        headerClass: 'col-time',
        tdClass: 'col-time font-mono text-sm',
        render: (r) => r.SRCREATIONTIME || '—',
      },
      {
        id: 'UP_TIME',
        label: 'UP_TIME',
        headerClass: 'col-time',
        tdClass: 'col-time font-mono text-sm',
        render: (r) => r.UP_TIME || '—',
      },
      {
        id: 'Submit Date',
        label: 'Submit Date',
        headerClass: 'col-time',
        tdClass: 'col-time font-mono text-sm',
        render: (r) => r['Submit Date'] || '—',
      },
      {
        id: 'DESCRIPTION',
        label: 'DESCRIPTION',
        headerClass: 'col-desc',
        tdClass: 'col-desc',
        render: (r) => (
          <span className="desc-full-text" title={r.DESCRIPTION || ''}>
            {r.DESCRIPTION || '—'}
          </span>
        ),
      }
    )

    if (isUnstitchedCategory) {
      cols.push({
        id: 'AUTOMATION_RCA_CONCLUSION_TEXT',
        label: 'AUTOMATION RCA CONCLUSION',
        headerClass: 'col-rca',
        tdClass: 'col-rca text-desc',
        render: (r) => {
          const val =
            r.AUTOMATION_RCA_CONCLUSION_TEXT ??
            r['AUTOMATION RCA CONCLUSION TEXT'] ??
            r.AUTOMATION_RCA_CONCLUSION ??
            r.automation_rca_conclusion_text ??
            ''
          return (
            <span title={val || ''}>
              {val
                ? val.length > 80
                  ? `${val.slice(0, 80)}...`
                  : val
                : '—'}
            </span>
          )
        },
      })
    }

    return cols
  }, [isDifferentNsttCategory, isManualCaptured, isUnstitchedCategory, bifurcationQuery])

  // Filter & sort records
  const filteredRecords = useMemo(() => {
    let result = records

    // Apply active column filters
    const activeColIds = Object.keys(columnFilters).filter((colId) => {
      const selected = columnFilters[colId]
      return selected instanceof Set
    })

    if (activeColIds.length > 0) {
      result = result.filter((rec) => {
        return activeColIds.every((colId) => {
          const allowedSet = columnFilters[colId]
          const allowedUpperSet = new Set(
            Array.from(allowedSet).map((v) => String(v).trim().toUpperCase())
          )

          if (colId === 'AUTOMATION_UPDATE_NSTT_NUMBER') {
            const val = getRecordValue(rec, colId)
            const tokens = parseIdTokens(val)
            if (tokens.length === 0) {
              return allowedSet.has('(Blanks)') || allowedUpperSet.has('(BLANKS)')
            }
            return tokens.some(
              (t) => allowedSet.has(t) || allowedUpperSet.has(t.toUpperCase())
            )
          }

          const val = getRecordValue(rec, colId)
          const displayVal = toDisplayVal(val)
          return (
            allowedSet.has(displayVal) ||
            allowedUpperSet.has(String(displayVal).trim().toUpperCase())
          )
        })
      })
    }

    // Apply sorting if configured
    if (sortConfig && sortConfig.colId) {
      const { colId, direction } = sortConfig
      result = [...result].sort((a, b) => {
        const valA = getRecordValue(a, colId)
        const valB = getRecordValue(b, colId)
        const cmp = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' })
        return direction === 'desc' ? -cmp : cmp
      })
    }

    return result
  }, [records, columnFilters, sortConfig])

  // Compute available distinct values and counts for a column
  // (evaluates against records matching all other active filters to provide accurate contextual counts)
  const getAvailableValuesForColumn = useCallback(
    (colId) => {
      const otherColIds = Object.keys(columnFilters).filter(
        (id) => id !== colId && columnFilters[id] instanceof Set
      )

      let baseRecords = records
      if (otherColIds.length > 0) {
        baseRecords = baseRecords.filter((rec) => {
          return otherColIds.every((otherId) => {
            const allowedSet = columnFilters[otherId]
            const allowedUpperSet = new Set(
              Array.from(allowedSet).map((v) => String(v).trim().toUpperCase())
            )

            if (otherId === 'AUTOMATION_UPDATE_NSTT_NUMBER') {
              const val = getRecordValue(rec, otherId)
              const tokens = parseIdTokens(val)
              if (tokens.length === 0) {
                return allowedSet.has('(Blanks)') || allowedUpperSet.has('(BLANKS)')
              }
              return tokens.some(
                (t) => allowedSet.has(t) || allowedUpperSet.has(t.toUpperCase())
              )
            }

            const val = getRecordValue(rec, otherId)
            const displayVal = toDisplayVal(val)
            return (
              allowedSet.has(displayVal) ||
              allowedUpperSet.has(String(displayVal).trim().toUpperCase())
            )
          })
        })
      }

      const countsMap = new Map()
      const isMultiIdCol = colId === 'AUTOMATION_UPDATE_NSTT_NUMBER'

      baseRecords.forEach((rec) => {
        const val = getRecordValue(rec, colId)
        if (isMultiIdCol) {
          const tokens = parseIdTokens(val)
          if (tokens.length === 0) {
            countsMap.set('(Blanks)', (countsMap.get('(Blanks)') || 0) + 1)
          } else {
            const uniqueTokensInRow = Array.from(new Set(tokens))
            uniqueTokensInRow.forEach((tok) => {
              countsMap.set(tok, (countsMap.get(tok) || 0) + 1)
            })
          }
        } else {
          const displayVal = toDisplayVal(val)
          countsMap.set(displayVal, (countsMap.get(displayVal) || 0) + 1)
        }
      })

      // Include all distinct values from all records so user can always re-enable options
      records.forEach((rec) => {
        const val = getRecordValue(rec, colId)
        if (isMultiIdCol) {
          const tokens = parseIdTokens(val)
          if (tokens.length === 0) {
            if (!countsMap.has('(Blanks)')) countsMap.set('(Blanks)', 0)
          } else {
            tokens.forEach((tok) => {
              if (!countsMap.has(tok)) countsMap.set(tok, 0)
            })
          }
        } else {
          const displayVal = toDisplayVal(val)
          if (!countsMap.has(displayVal)) {
            countsMap.set(displayVal, 0)
          }
        }
      })

      const sortedValues = Array.from(countsMap.keys()).sort((a, b) => {
        if (a === '(Blanks)') return 1
        if (b === '(Blanks)') return -1
        return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
      })

      return sortedValues.map((val) => ({
        value: val,
        count: countsMap.get(val) || 0,
      }))
    },
    [records, columnFilters]
  )

  // Filter actions
  const handleApplyColumnFilter = (colId, selectedValuesSet) => {
    const allAvailable = getAvailableValuesForColumn(colId)
    // If all available values or none are selected, treat as clearing the filter
    if (
      !selectedValuesSet ||
      selectedValuesSet.size === 0 ||
      selectedValuesSet.size >= allAvailable.length ||
      allAvailable.every((item) => selectedValuesSet.has(item.value))
    ) {
      handleClearColumnFilter(colId)
      return
    }

    setColumnFilters((prev) => ({
      ...prev,
      [colId]: selectedValuesSet,
    }))
    setCurrentPage(1)
    hasAutoScrolledRef.current = true
    if (tableWrapperRef.current) {
      tableWrapperRef.current.scrollTop = 0
    }
  }

  const handleClearColumnFilter = (colId) => {
    setColumnFilters((prev) => {
      const next = { ...prev }
      delete next[colId]
      return next
    })
    // If this column had active sorting, reset it back to original state
    setSortConfig((prevSort) => (prevSort?.colId === colId ? null : prevSort))
    // Close open dropdown for this column
    setOpenDropdownCol(null)
    // Clear any previous bifurcation locator search highlight
    if (setBifurcationQuery) {
      setBifurcationQuery('')
    }
    setCurrentPage(1)
    hasAutoScrolledRef.current = true
    if (tableWrapperRef.current) {
      tableWrapperRef.current.scrollTop = 0
    }
  }

  const handleClearAllFilters = () => {
    setColumnFilters({})
    setSortConfig(null)
    setOpenDropdownCol(null)
    if (setBifurcationQuery) {
      setBifurcationQuery('')
    }
    setCurrentPage(1)
    hasAutoScrolledRef.current = true
    if (tableWrapperRef.current) {
      tableWrapperRef.current.scrollTop = 0
    }
  }

  const handleSort = (colId, direction) => {
    setSortConfig({ colId, direction })
    setCurrentPage(1)
    hasAutoScrolledRef.current = true
    if (tableWrapperRef.current) {
      tableWrapperRef.current.scrollTop = 0
    }
  }

  const toggleFilterDropdown = (colId, e) => {
    e.stopPropagation()
    setOpenDropdownCol((prev) => (prev === colId ? null : colId))
  }

  // Active filter count (tracks active column filters only)
  const activeFilterCount = useMemo(() => {
    return Object.keys(columnFilters).filter(
      (colId) => columnFilters[colId] instanceof Set && columnFilters[colId].size > 0
    ).length
  }, [columnFilters])

  // Pagination slice
  const totalRecords = filteredRecords.length
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize))
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredRecords.slice(start, start + pageSize)
  }, [filteredRecords, currentPage, pageSize])

  if (!isDrilldownOpen) return null

  // Format category title nicely
  const formatCategoryTitle = (cat) => {
    if (!cat) return 'Record Drilldown'
    return cat
      .split('.')
      .map((part) => part.replace(/_/g, ' ').toUpperCase())
      .join(' ➔ ')
  }

  const exportToCsv = () => {
    if (!filteredRecords.length) return
    const excludedCols = new Set([
      'capture_type',
      'nstt_type',
      'CAPTURE_TYPE',
      'NSTT_TYPE',
      'is_total_sr',
      'is_nstt',
    ])
    if (!isDifferentNsttCategory) {
      excludedCols.add('AUTOMATION_IMPACT')
      excludedCols.add('automation_impact')
    }
    if (isManualCaptured) {
      excludedCols.add('AUTOMATION_UPDATE_NSTT_NUMBER')
      excludedCols.add('automation_update_nstt_number')
    }
    const headers = Object.keys(filteredRecords[0]).filter((h) => !excludedCols.has(h))
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
    link.download = `NSTT_Drilldown_${drilldownCategory || 'export'}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="drilldown-backdrop" onClick={closeDrilldown} role="dialog" aria-modal="true">
      <div className="drilldown-drawer" onClick={(e) => e.stopPropagation()}>
        {/* ── Drawer Header ────────────────────────────────────── */}
        <div className="drilldown-header">
          <div className="drilldown-header-title">
            <span className="drilldown-badge">Drill-down Records</span>
            <h2>{formatCategoryTitle(drilldownCategory)}</h2>
            <p className="drilldown-meta">
              Showing <strong>{totalRecords.toLocaleString()}</strong> record{totalRecords === 1 ? '' : 's'}
              {activeFilterCount > 0 && (
                <span className="filter-count-meta">
                  {' '}
                  (filtered from {records.length.toLocaleString()})
                </span>
              )}
            </p>
          </div>

          <div className="drilldown-header-actions">
            {records.length > 0 && (
              <button type="button" className="btn-drill-export" onClick={exportToCsv}>
                ⬇ Export CSV
              </button>
            )}
            <button
              type="button"
              className="btn-drill-close"
              onClick={closeDrilldown}
              aria-label="Close drawer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* ── Excel-style Filter Summary Bar & Controls ────────── */}
        <div className="drilldown-controls">
          <div className="drill-filter-summary">
            {activeFilterCount > 0 ? (
              <div className="active-filters-bar">
                <span className="filter-summary-label">
                  Active Filters ({activeFilterCount}):
                </span>
                <div className="filter-pills-list">
                  {Object.entries(columnFilters).map(([colId, valSet]) => {
                    const col = columns.find((c) => c.id === colId)
                    const label = col?.label || colId
                    const valsArray = Array.from(valSet)
                    const valText =
                      valsArray.length === 0
                        ? 'None selected'
                        : valsArray.length <= 2
                          ? valsArray.join(', ')
                          : `${valsArray.slice(0, 2).join(', ')} +${valsArray.length - 2} more`

                    return (
                      <span key={colId} className="active-filter-pill">
                        <strong className="pill-col-name">{label}:</strong> {valText}
                        <button
                          type="button"
                          className="btn-remove-pill"
                          onClick={() => handleClearColumnFilter(colId)}
                          title={`Clear ${label} filter`}
                          aria-label={`Clear ${label} filter`}
                        >
                          ✕
                        </button>
                      </span>
                    )
                  })}
                </div>
                <button
                  type="button"
                  className="btn-clear-all-filters"
                  onClick={handleClearAllFilters}
                >
                  ✕ Clear All Filters
                </button>
              </div>
            ) : null}
          </div>

          <div className="drill-page-size">
            <label htmlFor="drill-page-size-select">Per page:</label>
            <select
              id="drill-page-size-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setCurrentPage(1)
                if (tableWrapperRef.current) {
                  tableWrapperRef.current.scrollTop = 0
                }
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        {/* ── Table Body ───────────────────────────────────────── */}
        <div className="drilldown-body">
          {isDrilldownLoading ? (
            <div className="drilldown-loading">
              <div className="drilldown-spinner" />
              <p>Fetching records for {drilldownCategory}...</p>
            </div>
          ) : totalRecords === 0 ? (
            <div className="drilldown-empty">
              <span className="empty-icon">📂</span>
              <h3>No matching records</h3>
              <p>
                {activeFilterCount > 0
                  ? 'No records match the active column filters. Try adjusting or clearing filters.'
                  : 'No records found in this category.'}
              </p>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  className="btn-drill-clear-empty"
                  onClick={handleClearAllFilters}
                >
                  Clear All Filters
                </button>
              )}
            </div>
          ) : (
            <div ref={tableWrapperRef} className="drilldown-table-wrapper">
              <table className="drilldown-table">
                <thead>
                  <tr>
                    <th className="sticky-col">#</th>
                    {columns.map((col, idx) => {
                      const isFiltered = Boolean(
                        columnFilters[col.id] && columnFilters[col.id] instanceof Set
                      )
                      const isSorted = sortConfig?.colId === col.id
                      const isOpen = openDropdownCol === col.id
                      const alignRight = idx >= columns.length - 3

                      return (
                        <th
                          key={col.id}
                          className={`${col.headerClass || ''} ${isOpen ? 'dropdown-open' : ''
                            } ${isFiltered ? 'th-filtered' : ''}`}
                        >
                          <div className="th-cell-wrapper">
                            <span className="th-label" title={col.label}>
                              {col.label}
                            </span>
                            <div className="th-actions">
                              {isSorted && (
                                <span
                                  className="th-sort-badge"
                                  title={`Sorted ${sortConfig.direction === 'asc' ? 'A to Z' : 'Z to A'
                                    }`}
                                >
                                  {sortConfig.direction === 'asc' ? '▲' : '▼'}
                                </span>
                              )}
                              <button
                                type="button"
                                className={`th-filter-btn ${isFiltered ? 'is-filtered' : ''}`}
                                onClick={(e) => toggleFilterDropdown(col.id, e)}
                                title={
                                  isFiltered
                                    ? `Filtered by ${col.label} (click to modify)`
                                    : `Filter by ${col.label}`
                                }
                                aria-label={`Filter by ${col.label}`}
                                data-col={col.id}
                              >
                                <FilterIcon isFiltered={isFiltered} />
                              </button>
                            </div>

                            {isOpen && (
                              <ExcelFilterDropdown
                                column={col}
                                alignRight={alignRight}
                                availableValues={getAvailableValuesForColumn(col.id)}
                                currentFilter={columnFilters[col.id]}
                                currentSort={sortConfig}
                                onApplyFilter={(newSelected) =>
                                  handleApplyColumnFilter(col.id, newSelected)
                                }
                                onClearFilter={() => handleClearColumnFilter(col.id)}
                                onSort={(dir) => handleSort(col.id, dir)}
                                onClose={() => setOpenDropdownCol(null)}
                              />
                            )}
                          </div>
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody>
                  {paginatedRecords.map((r, i) => {
                    const rowIdx = (currentPage - 1) * pageSize + i + 1
                    const isMatched = isRecordMatchingSearch(r)
                    const incId = getRecordValue(r, 'INCIDENTID')
                    const srNo = getRecordValue(r, 'SR_NUMBER')
                    const uniqueKey = `${incId || 'row'}_${srNo || 'sr'}_${r.id ?? rowIdx}`
                    return (
                      <tr
                        key={uniqueKey}
                        className={isMatched ? 'drilldown-row-highlighted' : ''}
                      >
                        <td className={`sticky-col text-muted${isMatched ? ' drilldown-cell-highlighted' : ''}`}>{rowIdx}</td>
                        {columns.map((col) => (
                          <td key={col.id} className={`${col.tdClass}${isMatched ? ' drilldown-cell-highlighted' : ''}`}>
                            {col.render(r)}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Footer with Pagination ───────────────────────────── */}
        {totalRecords > 0 && (
          <div className="drilldown-footer">
            <span className="pagination-info">
              Showing {(currentPage - 1) * pageSize + 1} to{' '}
              {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} records
            </span>
            <div className="pagination-btns">
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === 1}
                onClick={() => {
                  setCurrentPage(1)
                  if (tableWrapperRef.current) tableWrapperRef.current.scrollTop = 0
                }}
              >
                « First
              </button>
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === 1}
                onClick={() => {
                  setCurrentPage((p) => Math.max(1, p - 1))
                  if (tableWrapperRef.current) tableWrapperRef.current.scrollTop = 0
                }}
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
                onClick={() => {
                  setCurrentPage((p) => Math.min(totalPages, p + 1))
                  if (tableWrapperRef.current) tableWrapperRef.current.scrollTop = 0
                }}
              >
                Next ›
              </button>
              <button
                type="button"
                className="page-btn"
                disabled={currentPage === totalPages}
                onClick={() => {
                  setCurrentPage(totalPages)
                  if (tableWrapperRef.current) tableWrapperRef.current.scrollTop = 0
                }}
              >
                Last »
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
