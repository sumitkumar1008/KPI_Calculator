import { useEffect, useRef, useState } from 'react'
import SummaryTableDrillDown from './TablesDrillDown'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary } from '../utils/drilldownUtils'

function AutomationRunTable({ sourceResponse }) {
  const { globalPeriod } = useGlobalFilter()
  const [tablePeriod, setTablePeriod] = useState(globalPeriod || 'monthly')
  const [rows, setRows] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // In-memory pre-warmed cache for all periods
  const cacheRef = useRef({})

  // Pre-calculate and cache all periods immediately upon upload
  useEffect(() => {
    if (!sourceResponse || !Array.isArray(sourceResponse.rows)) {
      cacheRef.current = {}
      setRows([])
      return
    }

    const rawRows = sourceResponse.rows
    cacheRef.current = {
      monthly: calculatePeriodSummary(rawRows, 'monthly', 'automation_run'),
      weekly: calculatePeriodSummary(rawRows, 'weekly', 'automation_run'),
      daily: calculatePeriodSummary(rawRows, 'daily', 'automation_run'),
    }

    setRows(cacheRef.current[tablePeriod] || [])
    setIsLoading(false)
    setError(null)
  }, [sourceResponse])

  // Sync tablePeriod ONLY when globalPeriod changes (e.g. from top Navbar GlobalFilter)
  useEffect(() => {
    if (globalPeriod) {
      setTablePeriod(globalPeriod)
    }
  }, [globalPeriod])

  // Update displayed rows instantly from pre-computed cache
  useEffect(() => {
    if (cacheRef.current[tablePeriod]) {
      setRows(cacheRef.current[tablePeriod])
    } else if (sourceResponse && Array.isArray(sourceResponse.rows)) {
      const computed = calculatePeriodSummary(sourceResponse.rows, tablePeriod, 'automation_run')
      cacheRef.current[tablePeriod] = computed
      setRows(computed)
    }
  }, [tablePeriod, sourceResponse])

  const columns = [
    { key: 'period', label: 'DATE / TIME' },
    { key: 'total_count', label: 'TOTAL COUNT' },
    { key: 'Y_count', label: 'YES' },
    { key: 'N_count', label: 'NO' },
    { key: 'Y_percentage', label: 'YES %' },
    { key: 'N_percentage', label: 'NO %' },
  ]

  const renderRow = (row) => {
    const total = row.total_count ?? ((row.Y_count ?? 0) + (row.N_count ?? 0))
    return (
      <>
        <td>{row.period_label || row.period || '—'}</td>
        <td>{total}</td>
        <td>{row.Y_count ?? 0}</td>
        <td>{row.N_count ?? 0}</td>
        <td>{row.Y_percentage ?? 0}%</td>
        <td>{row.N_percentage ?? 0}%</td>
      </>
    )
  }

  const activeTotalCount = rows.reduce((sum, r) => sum + (r.total_count ?? ((r.Y_count ?? 0) + (r.N_count ?? 0))), 0)
  const activeTotalY = rows.reduce((sum, r) => sum + (r.Y_count ?? 0), 0)
  const activeTotalN = rows.reduce((sum, r) => sum + (r.N_count ?? 0), 0)
  const activeTotalYPct = activeTotalCount ? Number(((activeTotalY / activeTotalCount) * 100).toFixed(2)) : 0
  const activeTotalNPct = activeTotalCount ? Number(((activeTotalN / activeTotalCount) * 100).toFixed(2)) : 0

  const headerStats = rows.length > 0 ? (
    <div className="summary-badge-group">
      <span className="summary-badge summary-badge-total">
        Total Records: <strong>{activeTotalCount}</strong>
      </span>
      <span className="summary-badge summary-badge-yes">
        Yes: <strong>{activeTotalY}</strong> ({activeTotalYPct}%)
      </span>
      <span className="summary-badge summary-badge-no">
        No: <strong>{activeTotalN}</strong> ({activeTotalNPct}%)
      </span>
    </div>
  ) : null

  return (
    <SummaryTableDrillDown
      sectionId="automation-run-counts"
      title="AUTOMATION RCA RUN COUNTS"
      subtitle="Automation Rca Run"
      tableType="automation_run"
      sourceResponse={sourceResponse}
      columns={columns}
      renderRow={renderRow}
      headerStats={headerStats}
      defaultPeriodRows={rows}
      isLoadingDefault={isLoading}
      errorDefault={error}
      period={tablePeriod}
      onPeriodChange={setTablePeriod}
    />
  )
}

export default AutomationRunTable
