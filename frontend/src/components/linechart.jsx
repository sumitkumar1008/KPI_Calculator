import { useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './linechart.css'

function LineChartComponent({
  data,
  period,
  onPeriodChange,
  isLoading,
  error,
  title = 'Line chart',
  label = 'Trend',
  emptyMessage = 'No chart data was returned for this period.',
}) {
  const [lineFilter, setLineFilter] = useState('both')
  const [hoveredLine, setHoveredLine] = useState(null)
  const showYes = lineFilter === 'both' || lineFilter === 'yes'
  const showNo = lineFilter === 'both' || lineFilter === 'no'

  const chartTooltip = ({ active, payload, label: tooltipLabel }) => {
    if (!active || !payload?.length) return null

    return (
      <div className="line-chart-tooltip">
        <p className="line-chart-tooltip__label">{tooltipLabel}</p>
        {payload.map((entry) => (
          <p key={entry.dataKey} style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }

  return (
    <section className="line-chart-section" aria-labelledby="line-chart-heading">
      <div className="line-chart-heading">
        <div>
          <p className="section-label">{label}</p>
          <h3 id="line-chart-heading">{title}</h3>
        </div>
        <label className="summary-period">
          <span>Time period</span>
          <select value={period} onChange={onPeriodChange} disabled={isLoading}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      </div>
      {error && <p className="message message--error summary-message" role="alert"><span aria-hidden="true">!</span>{error}</p>}
      {isLoading ? (
        <p className="empty-results">Loading {period} chart...</p>
      ) : data.length > 0 ? (
        <div className="line-chart-wrap">
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={data} margin={{ top: 12, right: 20, left: 4, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis dataKey="date" stroke="var(--muted)" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} stroke="var(--muted)" tick={{ fontSize: 11 }} />
              <Tooltip content={chartTooltip} />
              {showYes && (
                <Line
                  type="monotone"
                  dataKey="Y"
                  name="Yes"
                  stroke="#269653"
                  strokeWidth={hoveredLine === 'Y' ? 4 : 2.5}
                  style={{ filter: hoveredLine === 'Y' ? 'drop-shadow(0 0 6px #269653)' : 'none' }}
                  dot={{ r: 3 }}
                  activeDot={{ r: 6 }}
                  onMouseEnter={() => setHoveredLine('Y')}
                  onMouseLeave={() => setHoveredLine(null)}
                />
              )}
              {showNo && (
                <Line
                  type="monotone"
                  dataKey="N"
                  name="No"
                  stroke="#c94b4b"
                  strokeWidth={hoveredLine === 'N' ? 4 : 2.5}
                  style={{ filter: hoveredLine === 'N' ? 'drop-shadow(0 0 6px #c94b4b)' : 'none' }}
                  dot={{ r: 3 }}
                  activeDot={{ r: 6 }}
                  onMouseEnter={() => setHoveredLine('N')}
                  onMouseLeave={() => setHoveredLine(null)}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
          <div className="line-chart-toggle" aria-label="Choose chart lines">
            <button
              type="button"
              className={`line-toggle line-toggle--yes ${lineFilter === 'yes' ? 'is-active' : ''}`}
              onClick={() => setLineFilter((currentFilter) => currentFilter === 'yes' ? 'both' : 'yes')}
              aria-pressed={lineFilter === 'yes'}
            >
              Y
            </button>
            <button
              type="button"
              className={`line-toggle line-toggle--no ${lineFilter === 'no' ? 'is-active' : ''}`}
              onClick={() => setLineFilter((currentFilter) => currentFilter === 'no' ? 'both' : 'no')}
              aria-pressed={lineFilter === 'no'}
            >
              N
            </button>
          </div>
        </div>
      ) : (
        <p className="empty-results">{emptyMessage}</p>
      )}
    </section>
  )
}

export default LineChartComponent
