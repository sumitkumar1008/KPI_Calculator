import { useEffect, useMemo, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, filterRowsByMediaAndRoster, formatSecondsToHHMMSS, parseDurationToSeconds } from '../utils/drilldownUtils'

const series = [
  { key: 'MTTI', name: 'MTTI', color: '#8e44ad' },
  { key: 'MTTA', name: 'MTTA', color: '#d4a017' },
  { key: 'MTTAck', name: 'MTTAck', color: '#2563eb' },
]

function ShortResponseTimeLineChart({ sourceResponse }) {
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

  // Sync with global filter changes
  useEffect(() => {
    if (globalPeriod) setPeriod(globalPeriod)
  }, [globalPeriod])

  useEffect(() => {
    if (globalMedia !== undefined) setMedia(globalMedia)
  }, [globalMedia])

  useEffect(() => {
    if (globalRoster !== undefined) setRoster(globalRoster)
  }, [globalRoster])

  // Filter rows based on local media & roster selection
  const filteredChartRows = useMemo(() => {
    const baseRows = rawResponse?.rows || sourceResponse?.rows || []
    return filterRowsByMediaAndRoster(baseRows, media, roster)
  }, [rawResponse, sourceResponse, media, roster])

  useEffect(() => {
    if (!filteredChartRows || filteredChartRows.length === 0) {
      setChartData([])
      return
    }
    const summary = calculatePeriodSummary(filteredChartRows, period, 'avg')
    setChartData(summary.map((row) => ({
      date: row.period_label || row.period,
      MTTI: parseDurationToSeconds(row.AVG_MTTI),
      MTTA: parseDurationToSeconds(row.AVG_MTTA),
      MTTAck: parseDurationToSeconds(row.AVG_MTTAck),
    })))
  }, [filteredChartRows, period])

  return (
    <LineChartComponent
      sectionId="short-response-time-graph"
      data={chartData}
      period={period}
      onPeriodChange={(event) => setPeriod(event.target.value)}
      media={media}
      onMediaChange={(event) => setMedia(event.target.value)}
      roster={roster}
      onRosterChange={(event) => setRoster(event.target.value)}
      availableMediaOptions={availableMediaOptions}
      availableRosterOptions={availableRosterOptions}
      isLoading={false}
      error={null}
      series={series}
      valueFormatter={formatSecondsToHHMMSS}
      label="GRAPH OF MTTI,MTTA,MTTAck"
      title="UNIFIED KPI GRAPH"
      emptyMessage="No short average response-time data was returned for this filter selection."
    />
  )
}

export default ShortResponseTimeLineChart
