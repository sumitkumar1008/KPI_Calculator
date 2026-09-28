import { useEffect, useMemo, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, filterRowsByMediaAndRoster, formatSecondsToHHMMSS, parseDurationToSeconds } from '../utils/drilldownUtils'

const series = [
  { key: 'MTTR', name: 'MTTR', color: '#e75480' },
  { key: 'MTTr', name: 'MTTr', color: '#f28c28' },
]

function LongResponseTimeLineChart({ sourceResponse }) {
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
      MTTR: parseDurationToSeconds(row.AVG_MTTR),
      MTTr: parseDurationToSeconds(row.AVG_MTTr),
    })))
  }, [filteredChartRows, period])

  return (
    <LineChartComponent
      sectionId="long-response-time-graph"
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
      label="GRAPH OF MTTR AND MTTr"
      title="UNIFIED KPI GRAPH"
      emptyMessage="No long average response-time data was returned for this filter selection."
    />
  )
}

export default LongResponseTimeLineChart
