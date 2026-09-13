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
  sectionId,
  label = 'Trend',
  emptyMessage = 'No chart data was returned for this period.',
  series = [
    { key: 'Y', name: 'Yes', color: '#269653' },
    { key: 'N', name: 'No', color: '#c94b4b' },
  ],
  valueUnit = '',
}) {
  const [lineFilter, setLineFilter] = useState('both')
  const [hoveredLine, setHoveredLine] = useState(null)

  const chartTooltip = ({ active, payload, label: tooltipLabel }) => {
    if (!active || !payload?.length) return null

    return (
      <div className="line-chart-tooltip">
        <p className="line-chart-tooltip__label">{tooltipLabel}</p>
        {payload.map((entry) => (
          <p key={entry.dataKey} style={{ color: entry.color }}>
            {entry.name}: {entry.value}{valueUnit ? ` ${valueUnit}` : ''}
          </p>
        ))}
      </div>
    )
  }

  return (
    <section id={sectionId} className="line-chart-section" aria-labelledby="line-chart-heading">
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
              {series.map((line) => {
                if (lineFilter !== 'both' && lineFilter !== line.key) return null
                return (
                  <Line
                    key={line.key}
                    type="monotone"
                    dataKey={line.key}
                    name={line.name}
                    stroke={line.color}
                    strokeWidth={hoveredLine === line.key ? 4 : 2.5}
                    style={{ filter: hoveredLine === line.key ? `drop-shadow(0 0 6px ${line.color})` : 'none' }}
                    dot={{ r: 3 }}
                    activeDot={{ r: 6 }}
                    onMouseEnter={() => setHoveredLine(line.key)}
                    onMouseLeave={() => setHoveredLine(null)}
                  />
                )
              })}
            </LineChart>
          </ResponsiveContainer>
          <div className="line-chart-toggle" aria-label="Choose chart lines">
            {series.map((line) => (
              <button
                key={line.key}
                type="button"
                className={`line-toggle ${lineFilter === line.key ? 'is-active' : ''}`}
                style={lineFilter === line.key ? { borderColor: line.color, color: line.color, background: `${line.color}1f` } : undefined}
                onClick={() => setLineFilter((currentFilter) => currentFilter === line.key ? 'both' : line.key)}
                aria-pressed={lineFilter === line.key}
              >
                {line.name}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="empty-results">{emptyMessage}</p>
      )}
    </section>
  )
}

export default LineChartComponent
