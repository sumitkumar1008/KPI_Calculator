import { useEffect, useMemo, useRef, useState } from 'react'
import SummaryTableDrillDown from './TablesDrillDown'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, filterRowsByMediaAndRoster } from '../utils/drilldownUtils'

function AvgTable({ sourceResponse }) {
  const {
    globalPeriod,
    selectedMedia: globalMedia,
    selectedRoster: globalRoster,
    availableMediaOptions,
    availableRosterOptions,
    rawResponse,
  } = useGlobalFilter()

  const [tablePeriod, setTablePeriod] = useState(globalPeriod || 'monthly')
  const [media, setMedia] = useState(globalMedia || 'all')
  const [roster, setRoster] = useState(globalRoster || 'all')
  const [rows, setRows] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // In-memory pre-warmed cache for all periods
  const cacheRef = useRef({})

  // Sync with global filter changes
  useEffect(() => {
    if (globalPeriod) {
      setTablePeriod(globalPeriod)
    }
  }, [globalPeriod])

  useEffect(() => {
    if (globalMedia !== undefined) {
      setMedia(globalMedia)
    }
  }, [globalMedia])

  useEffect(() => {
    if (globalRoster !== undefined) {
      setRoster(globalRoster)
    }
  }, [globalRoster])

  // Filter rows based on local media & roster selection
  const filteredTableRows = useMemo(() => {
    const baseRows = rawResponse?.rows || sourceResponse?.rows || []
    return filterRowsByMediaAndRoster(baseRows, media, roster)
  }, [rawResponse, sourceResponse, media, roster])

  // Pre-calculate and cache all periods immediately upon rows change
  useEffect(() => {
    if (!filteredTableRows || filteredTableRows.length === 0) {
      cacheRef.current = {}
      setRows([])
      return
    }

    cacheRef.current = {
      monthly: calculatePeriodSummary(filteredTableRows, 'monthly', 'avg'),
      weekly: calculatePeriodSummary(filteredTableRows, 'weekly', 'avg'),
      daily: calculatePeriodSummary(filteredTableRows, 'daily', 'avg'),
    }

    setRows(cacheRef.current[tablePeriod] || [])
    setIsLoading(false)
    setError(null)
  }, [filteredTableRows, tablePeriod])

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
      sectionId="unified-kpi"
      title="UNIFIED KPI"
      subtitle="KPI summary"
      tableType="avg"
      sourceResponse={sourceResponse}
      filteredRows={filteredTableRows}
      columns={columns}
      renderRow={renderRow}
      defaultPeriodRows={rows}
      isLoadingDefault={isLoading}
      errorDefault={error}
      period={tablePeriod}
      onPeriodChange={setTablePeriod}
      media={media}
      onMediaChange={(e) => setMedia(e.target.value)}
      roster={roster}
      onRosterChange={(e) => setRoster(e.target.value)}
      availableMediaOptions={availableMediaOptions}
      availableRosterOptions={availableRosterOptions}
    />
  )
}

export default AvgTable