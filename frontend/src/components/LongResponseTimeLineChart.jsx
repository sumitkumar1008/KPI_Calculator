import { useEffect, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, parseDurationToSeconds } from '../utils/drilldownUtils'

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
      MTTR: toHours(row.AVG_MTTR),
      MTTr: toHours(row.AVG_MTTr),
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
      valueUnit="hr"
      label="Average response time"
      title="UNIFIED KPI GRAPH"
      emptyMessage="No long average response-time data was returned for this period."
    />
  )
}

function toHours(value) {
  const seconds = parseDurationToSeconds(value)
  return seconds === null ? null : Number((seconds / 3600).toFixed(2))
}

export default LongResponseTimeLineChart
