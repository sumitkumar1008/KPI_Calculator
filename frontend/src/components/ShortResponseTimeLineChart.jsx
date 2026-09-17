import { useEffect, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary, formatSecondsToHHMMSS, parseDurationToSeconds } from '../utils/drilldownUtils'

const series = [
  { key: 'MTTI', name: 'MTTI', color: '#8e44ad' },
  { key: 'MTTA', name: 'MTTA', color: '#d4a017' },
  { key: 'MTTAck', name: 'MTTAck', color: '#2563eb' },
]

function ShortResponseTimeLineChart({ sourceResponse }) {
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
      MTTI: parseDurationToSeconds(row.AVG_MTTI),
      MTTA: parseDurationToSeconds(row.AVG_MTTA),
      MTTAck: parseDurationToSeconds(row.AVG_MTTAck),
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
      label="GRAPH OF MTTI,MTTA,MTTAck"
      title="UNIFIED KPI GRAPH"
      emptyMessage="No short average response-time data was returned for this period."
    />
  )
}

export default ShortResponseTimeLineChart
