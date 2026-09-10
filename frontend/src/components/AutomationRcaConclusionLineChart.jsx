import { useEffect, useRef, useState } from 'react'
import LineChartComponent from './linechart'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import { calculatePeriodSummary } from '../utils/drilldownUtils'

function AutomationRcaConclusionLineChart({ sourceResponse }) {
  const { globalPeriod } = useGlobalFilter()
  const [period, setPeriod] = useState(globalPeriod || 'monthly')
  const [chartData, setChartData] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const cacheRef = useRef({})

  // Pre-calculate all period trends immediately when file is uploaded
  useEffect(() => {
    if (!sourceResponse || !Array.isArray(sourceResponse.rows)) {
      cacheRef.current = {}
      setChartData([])
      return
    }

    const rawRows = sourceResponse.rows
    const formatData = (summary) =>
      (summary || []).map((row) => ({
        date: row.period_label || row.period,
        Y: Number(row.Y_count ?? 0),
        N: Number(row.N_count ?? 0),
      }))

    cacheRef.current = {
      monthly: formatData(calculatePeriodSummary(rawRows, 'monthly', 'automation_rca')),
      weekly: formatData(calculatePeriodSummary(rawRows, 'weekly', 'automation_rca')),
      daily: formatData(calculatePeriodSummary(rawRows, 'daily', 'automation_rca')),
    }

    setChartData(cacheRef.current[period] || [])
    setIsLoading(false)
    setError(null)
  }, [sourceResponse])

  // Sync chart period ONLY when globalPeriod changes (e.g. from top Navbar GlobalFilter)
  useEffect(() => {
    if (globalPeriod) {
      setPeriod(globalPeriod)
    }
  }, [globalPeriod])

  // Update chart data instantly from cache or fallback calculation/fetch
  useEffect(() => {
    if (cacheRef.current[period]) {
      setChartData(cacheRef.current[period])
      return
    }

    if (sourceResponse && Array.isArray(sourceResponse.rows)) {
      const summary = calculatePeriodSummary(sourceResponse.rows, period, 'automation_rca')
      const formatted = (summary || []).map((row) => ({
        date: row.period_label || row.period,
        Y: Number(row.Y_count ?? 0),
        N: Number(row.N_count ?? 0),
      }))
      cacheRef.current[period] = formatted
      setChartData(formatted)
      return
    }

    if (!sourceResponse) return

    // Fallback API call if sourceResponse.rows is absent
    const controller = new AbortController()
    const endpoint = new URL(
      import.meta.env.VITE_AUTOMATION_RCA_API_ENDPOINT || 'http://127.0.0.1:5000/api/v1/kpi/automation-rca-conclusion',
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
        const formatted = (data.summary || []).map((row) => ({
          date: row.period_label || row.period,
          Y: Number(row.Y_count ?? 0),
          N: Number(row.N_count ?? 0),
        }))
        cacheRef.current[period] = formatted
        setChartData(formatted)
      })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setChartData([])
          setError(loadError.message || 'RCA conclusion chart data could not be loaded.')
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
      label="RCA conclusion trend"
      title="RCA conclusion Y/N trend"
      emptyMessage="No RCA conclusion chart data was returned for this period."
    />
  )
}

export default AutomationRcaConclusionLineChart

