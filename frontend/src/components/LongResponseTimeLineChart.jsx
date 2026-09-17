import { useEffect, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, formatSecondsToHHMMSS, parseDurationToSeconds } from '../utils/drilldownUtils'

const series = [
  { key: 'MTTR', name: 'MTTR', color: '#e75480' },
  { key: 'MTTr', name: 'MTTr', color: '#f28c28' },
]

function LongResponseTimeLineChart({ sourceResponse }) {
  const { globalPeriod, setGlobalPeriod } = useGlobalFilter()
  const [period, setPeriod] = useState(globalPeriod || 'monthly')
  const [chartData, setChartData] = useState([])

  useEffect(() => {
    if (globalPeriod) setPeriod(globalPeriod)
  }, [globalPeriod])

  useEffect(() => {
    const rows = sourceResponse?.rows
    if (!Array.isArray(rows)) {
      setChartData([])
      return
    }
    const summary = calculatePeriodSummary(rows, period, 'avg')
    setChartData(summary.map((row) => ({
      date: row.period_label || row.period,
      MTTR: parseDurationToSeconds(row.AVG_MTTR),
      MTTr: parseDurationToSeconds(row.AVG_MTTr),
    })))
  }, [sourceResponse, period])

  return (
    <LineChartComponent
      data={chartData}
      period={period}
      onPeriodChange={(event) => {
        setPeriod(event.target.value)
        setGlobalPeriod(event.target.value)
      }}
      isLoading={false}
      error={null}
      series={series}
      valueFormatter={formatSecondsToHHMMSS}
      label="GRAPH OF MTTR AND MTTr"
      title="UNIFIED KPI GRAPH"
      emptyMessage="No long average response-time data was returned for this period."
    />
  )
}

export default LongResponseTimeLineChart
