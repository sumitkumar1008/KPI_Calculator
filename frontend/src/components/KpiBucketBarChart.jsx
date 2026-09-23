import { useMemo, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { parseDurationToSeconds } from '../utils/drilldownUtils'
import DownloadDropdown from './DownloadDropdown'
import { exportDataViaApi, exportSvgAsPng } from '../utils/exportUtils'
import './linechart.css'

/**
 * Time-range buckets for incident response KPIs.
 * Each bucket has a label, a lower bound (inclusive) and upper bound (exclusive) in seconds.
 */
const BUCKETS = [
  { label: '0–15 min', min: 0, max: 15 * 60 },
  { label: '15–30 min', min: 15 * 60, max: 30 * 60 },
  { label: '30 min–1 hr', min: 30 * 60, max: 60 * 60 },
  { label: '1–4 hr', min: 60 * 60, max: 4 * 3600 },
  { label: '4–12 hr', min: 4 * 3600, max: 12 * 3600 },
  { label: '12 hr+', min: 12 * 3600, max: Infinity },
]

const KPI_CONFIG = [
  { key: 'MTTI', label: 'MTTI', color: '#8e44ad' },
  { key: 'MTTR', label: 'MTTR', color: '#e75480' },
  { key: 'MTTr', label: 'MTTr', color: '#f28c28' },
]

/**
 * Bucketize raw rows for the three KPIs.
 * Returns an array of { bucket, MTTI, MTTR, MTTr } objects.
 */
function bucketizeRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return []

  // Initialize counts
  const counts = BUCKETS.map((b) => ({
    bucket: b.label,
    MTTI: 0,
    MTTR: 0,
    MTTr: 0,
  }))

  rows.forEach((row) => {
    KPI_CONFIG.forEach(({ key }) => {
      const secKey = `${key}_seconds`
      let seconds = null

      if (row[secKey] !== undefined && row[secKey] !== null && !isNaN(row[secKey])) {
        seconds = Number(row[secKey])
      } else {
        seconds = parseDurationToSeconds(row[key])
      }

      if (seconds === null || seconds < 0) return

      for (let i = 0; i < BUCKETS.length; i++) {
        if (seconds >= BUCKETS[i].min && seconds < BUCKETS[i].max) {
          counts[i][key]++
          break
        }
      }
    })
  })

  return counts
}

function KpiBucketBarChart({ sourceResponse }) {
  const [activeKpis, setActiveKpis] = useState(() => KPI_CONFIG.map((k) => k.key))
  const chartWrapRef = useRef(null)

  const chartData = useMemo(() => {
    return bucketizeRows(sourceResponse?.rows)
  }, [sourceResponse])

  const toggleKpi = (key) => {
    setActiveKpis((prev) => {
      if (prev.includes(key)) {
        if (prev.length === 1) return KPI_CONFIG.map((k) => k.key)
        return prev.filter((k) => k !== key)
      }
      return [...prev, key]
    })
  }

  const totalRecords = sourceResponse?.rows?.length ?? 0

  const handleExportData = (format) => {
    if (!chartData || chartData.length === 0) return

    const exportCols = [
      { key: 'bucket', label: 'Time Bucket' },
      { key: 'MTTI', label: 'MTTI (Record Count)' },
      { key: 'MTTR', label: 'MTTR (Record Count)' },
      { key: 'MTTr', label: 'MTTr (Record Count)' },
    ]

    return exportDataViaApi({
      format,
      filename: 'kpi_bucket_distribution',
      title: 'Incident Response Distribution (KPI Buckets)',
      sheetName: 'KPI Buckets',
      columns: exportCols,
      data: chartData,
    })
  }

  const handleExportImage = () => {
    if (!chartWrapRef.current) return
    return exportSvgAsPng(chartWrapRef.current, 'kpi_bucket_distribution_chart')
  }

  const chartTooltip = ({ active, payload, label: tooltipLabel }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="line-chart-tooltip">
        <p className="line-chart-tooltip__label">{tooltipLabel}</p>
        {payload.map((entry) => (
          <p key={entry.dataKey} style={{ color: entry.fill || entry.color }}>
            {entry.name}: {entry.value} record{entry.value !== 1 ? 's' : ''}{' '}
            ({totalRecords ? ((entry.value / totalRecords) * 100).toFixed(1) : 0}%)
          </p>
        ))}
      </div>
    )
  }

  const hasData = chartData.some((d) => d.MTTI > 0 || d.MTTR > 0 || d.MTTr > 0)

  return (
    <section id="kpi-bucket-chart" className="line-chart-section" aria-label="KPI Bucket Bar Chart">
      <div className="line-chart-heading">
        <div>
          <p className="section-label line-chart-label" style={{ textTransform: 'none' }}>
            Incident Response Distribution
          </p>
          <h3>KPI BUCKET BAR CHART — MTTI, MTTR, MTTr</h3>
        </div>
        <DownloadDropdown
          onDownloadExcel={() => handleExportData('xlsx')}
          onDownloadCsv={() => handleExportData('csv')}
          onDownloadImage={handleExportImage}
          disabled={!hasData}
          tooltip="Export KPI Bucket Bar Chart data or image"
        />
      </div>

      {hasData ? (
        <div className="line-chart-wrap" ref={chartWrapRef}>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={chartData} margin={{ top: 12, right: 20, left: 4, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis
                dataKey="bucket"
                stroke="var(--muted)"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-15}
                textAnchor="end"
                height={50}
              />
              <YAxis
                allowDecimals={false}
                stroke="var(--muted)"
                tick={{ fontSize: 11 }}
                label={{ value: 'Record Count', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: 'var(--muted)' } }}
              />
              <Tooltip content={chartTooltip} />
              <Legend
                verticalAlign="top"
                height={36}
                formatter={(value) => <span style={{ color: 'var(--ink)', fontSize: 12, fontWeight: 600 }}>{value}</span>}
              />
              {KPI_CONFIG.map((kpi) => {
                if (!activeKpis.includes(kpi.key)) return null
                return (
                  <Bar
                    key={kpi.key}
                    dataKey={kpi.key}
                    name={kpi.label}
                    fill={kpi.color}
                    radius={[4, 4, 0, 0]}
                    maxBarSize={42}
                  >
                    {chartData.map((entry, idx) => (
                      <Cell
                        key={`cell-${kpi.key}-${idx}`}
                        fill={kpi.color}
                        fillOpacity={entry[kpi.key] > 0 ? 1 : 0.25}
                      />
                    ))}
                  </Bar>
                )
              })}
            </BarChart>
          </ResponsiveContainer>

          <div className="line-chart-toggle" aria-label="Toggle KPI visibility">
            {KPI_CONFIG.map((kpi) => (
              <button
                key={kpi.key}
                type="button"
                className={`line-toggle ${activeKpis.includes(kpi.key) ? 'is-active' : ''}`}
                style={
                  activeKpis.includes(kpi.key)
                    ? { borderColor: kpi.color, color: kpi.color, background: `${kpi.color}1f` }
                    : undefined
                }
                onClick={() => toggleKpi(kpi.key)}
                aria-pressed={activeKpis.includes(kpi.key)}
              >
                {kpi.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="empty-results">No MTTI / MTTR / MTTr data available for bucketization.</p>
      )}
    </section>
  )
}

export default KpiBucketBarChart
