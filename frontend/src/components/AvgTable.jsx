function AvgTable({ rows, period, isLoading, error, onPeriodChange }) {
  return (
    <section className="summary-section" aria-labelledby="summary-heading">
      <div className="summary-heading">
        <div>
          <p className="section-label">KPI summary</p>
          <h3 id="summary-heading">Average response times</h3>
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
        <p className="empty-results">Loading {period} summary...</p>
      ) : rows.length > 0 ? (
        <div className="results-table-wrap">
          <table className="results-table summary-table">
            <thead>
              <tr>
                <th scope="col">TIME PERIOD</th>
                <th scope="col">AVG MTTA</th>
                <th scope="col">AVG MTTR</th>
                <th scope="col">AVG MTTAck</th>
                <th scope="col">AVG MTTI</th>
                <th scope="col">AVG MTTr</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.period}>
                  <td>{row.period_label || row.period || '—'}</td>
                  <td>{row.AVG_MTTA || '—'}</td>
                  <td>{row.AVG_MTTR || '—'}</td>
                  <td>{row.AVG_MTTAck || '—'}</td>
                  <td>{row.AVG_MTTI || '—'}</td>
                  <td>{row.AVG_MTTr || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-results">The API returned no summary rows. Confirm that the configured endpoint returns a top-level <code>summary</code> array for <code>group_by={period}</code>.</p>
      )}
    </section>
  )
}

export default AvgTable
