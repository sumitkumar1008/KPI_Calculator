import { useEffect, useState } from 'react'
import LineChartComponent from './linechart'

function AutomationRunLineChart({ sourceResponse }) {
  const [period, setPeriod] = useState('daily')
  const [chartData, setChartData] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!sourceResponse) return

    const controller = new AbortController()
    const endpoint = new URL(
      import.meta.env.VITE_AUTOMATION_RUN_API_ENDPOINT || 'http://127.0.0.1:5000/api/v1/kpi/automation-run',
      window.location.origin,
    )
    endpoint.searchParams.set('group_by', period)
    setIsLoading(true)
    setError(null)

    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourceResponse),
      signal: controller.signal,
    })
      .then(async (response) => {
        const data = await response.json()
        if (!response.ok) throw new Error(data?.error || `Server error HTTP ${response.status}.`)
        return data
      })
      .then((data) => {
        setChartData((data.summary || []).map((row) => ({
          date: row.period_label || row.period,
          Y: Number(row.Y_count ?? 0),
          N: Number(row.N_count ?? 0),
        })))
      })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setChartData([])
          setError(loadError.message || 'Automation run chart data could not be loaded.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [sourceResponse, period])

  return (
    <LineChartComponent
      data={chartData}
      period={period}
      onPeriodChange={(event) => setPeriod(event.target.value)}
      isLoading={isLoading}
      error={error}
      label="Automation run trend"
      title="Automation run Y/N trend"
      emptyMessage="No automation run chart data was returned for this period."
    />
  )
}

export default AutomationRunLineChart
