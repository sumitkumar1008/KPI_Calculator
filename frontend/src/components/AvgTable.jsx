import { useEffect, useRef, useState } from 'react'
import SummaryTableDrillDown from './TablesDrillDown'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary } from '../utils/drilldownUtils'

function AvgTable({ sourceResponse }) {
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

    // Pre-compute monthly, weekly, daily summaries in memory
    const rawRows = sourceResponse.rows
    cacheRef.current = {
      monthly: calculatePeriodSummary(rawRows, 'monthly', 'avg'),
      weekly: calculatePeriodSummary(rawRows, 'weekly', 'avg'),
      daily: calculatePeriodSummary(rawRows, 'daily', 'avg'),
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
      const computed = calculatePeriodSummary(sourceResponse.rows, tablePeriod, 'avg')
      cacheRef.current[tablePeriod] = computed
      setRows(computed)
    }
  }, [tablePeriod, sourceResponse])

  const columns = [
    { key: 'period', label: 'TIME PERIOD' },
    { key: 'MTTI', label: 'MTTI' },
    { key: 'MTTA', label: 'MTTA' },
    { key: 'MTTAck', label: 'MTTAck' },
    { key: 'MTTR', label: 'MTTR' },
    { key: 'MTTr', label: 'MTTr' },
  ]

  const renderRow = (row) => (
    <>
      <td>{row.period_label || row.period || '—'}</td>
      <td>{row.AVG_MTTI ?? '—'}</td>
      <td>{row.AVG_MTTA ?? '—'}</td>
      <td>{row.AVG_MTTAck ?? '—'}</td>
      <td>{row.AVG_MTTR ?? '—'}</td>
      <td>{row.AVG_MTTr ?? '—'}</td>
    </>
  )

  return (
    <SummaryTableDrillDown
      title="Average response times"
      subtitle="KPI summary"
      tableType="avg"
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

export default AvgTable
