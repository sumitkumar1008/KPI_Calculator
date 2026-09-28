import { useEffect, useMemo, useRef, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, filterRowsByMediaAndRoster } from '../utils/drilldownUtils'

function AutomationRcaConclusionLineChart({ sourceResponse }) {
  const {
    globalPeriod,
    selectedMedia: globalMedia,
    selectedRoster: globalRoster,
    availableMediaOptions,
    availableRosterOptions,
    rawResponse,
  } = useGlobalFilter()

  const [period, setPeriod] = useState(globalPeriod || 'monthly')
  const [media, setMedia] = useState(globalMedia || 'all')
  const [roster, setRoster] = useState(globalRoster || 'all')
  const [chartData, setChartData] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const cacheRef = useRef({})

  // Sync chart filters when global filters change
  useEffect(() => {
    if (globalPeriod) {
      setPeriod(globalPeriod)
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
  const filteredChartRows = useMemo(() => {
    const baseRows = rawResponse?.rows || sourceResponse?.rows || []
    return filterRowsByMediaAndRoster(baseRows, media, roster)
  }, [rawResponse, sourceResponse, media, roster])

  // Pre-calculate all period trends when filteredChartRows change
  useEffect(() => {
    if (!filteredChartRows || filteredChartRows.length === 0) {
      cacheRef.current = {}
      setChartData([])
      return
    }

    const formatData = (summary) =>
      (summary || []).map((row) => ({
        date: row.period_label || row.period,
        Y: Number(row.Y_count ?? 0),
        N: Number(row.N_count ?? 0),
        Y_percentage: Number(row.Y_percentage ?? 0),
        N_percentage: Number(row.N_percentage ?? 0),
      }))

    cacheRef.current = {
      monthly: formatData(calculatePeriodSummary(filteredChartRows, 'monthly', 'automation_rca')),
      weekly: formatData(calculatePeriodSummary(filteredChartRows, 'weekly', 'automation_rca')),
      daily: formatData(calculatePeriodSummary(filteredChartRows, 'daily', 'automation_rca')),
    }

    setChartData(cacheRef.current[period] || [])
    setIsLoading(false)
    setError(null)
  }, [filteredChartRows, period])

  return (
    <LineChartComponent
      sectionId="automation-conclusion-graph"
      data={chartData}
      period={period}
      onPeriodChange={(event) => setPeriod(event.target.value)}
      media={media}
      onMediaChange={(event) => setMedia(event.target.value)}
      roster={roster}
      onRosterChange={(event) => setRoster(event.target.value)}
      availableMediaOptions={availableMediaOptions}
      availableRosterOptions={availableRosterOptions}
      isLoading={isLoading}
      error={error}
      label="RCA conclusion trend"
      title="AUTOMATION RCA CONCLUSION Y/N GRAPH"
      emptyMessage="No RCA conclusion chart data was returned for this filter selection."
    />
  )
}

export default AutomationRcaConclusionLineChart

