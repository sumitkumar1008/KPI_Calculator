import { useEffect, useRef, useState } from 'react'
import SummaryTableDrillDown from './TablesDrillDown'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary } from '../utils/drilldownUtils'

function AutomationRcaConclusionTable({ sourceResponse }) {
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
      monthly: calculatePeriodSummary(rawRows, 'monthly', 'automation_rca'),
      weekly: calculatePeriodSummary(rawRows, 'weekly', 'automation_rca'),
      daily: calculatePeriodSummary(rawRows, 'daily', 'automation_rca'),
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
      const computed = calculatePeriodSummary(sourceResponse.rows, tablePeriod, 'automation_rca')
      cacheRef.current[tablePeriod] = computed
      setRows(computed)
    }
  }, [tablePeriod, sourceResponse])

  const columns = [
    { key: 'period', label: 'DATE / TIME' },
    { key: 'Y_count', label: 'Y' },
    { key: 'N_count', label: 'N' },
  ]

  const renderRow = (row) => (
    <>
      <td>{row.period_label || row.period || '—'}</td>
      <td>{row.Y_count ?? 0}</td>
      <td>{row.N_count ?? 0}</td>
    </>
  )

  return (
    <SummaryTableDrillDown
      title="Automation Rca Conclusion counts"
      subtitle="Automation Rca Conclusion"
      tableType="automation_rca"
      sourceResponse={sourceResponse}
      columns={columns}
      renderRow={renderRow}
      defaultPeriodRows={rows}
      isLoadingDefault={isLoading}
      errorDefault={error}
      period={tablePeriod}
      onPeriodChange={setTablePeriod}
    />
  )
}

export default AutomationRcaConclusionTable
