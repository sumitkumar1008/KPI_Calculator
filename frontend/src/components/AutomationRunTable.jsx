import { useEffect, useState } from 'react'

function AutomationRunTable({ sourceResponse }) {
  const [rows, setRows] = useState([])
  const [period, setPeriod] = useState('daily')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage))
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = rows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  useEffect(() => {
    setCurrentPage(1)
  }, [rows])

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
      .then((data) => setRows(Array.isArray(data.summary) ? data.summary : []))
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setRows([])
          setError(loadError.message || 'Automation run counts could not be loaded.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [sourceResponse, period])

  const changeRowsPerPage = (event) => {
    setRowsPerPage(Number(event.target.value))
    setCurrentPage(1)
  }

  return (
    <section className="summary-section" aria-labelledby="automation-run-heading">
      <div className="summary-heading">
        <div>
          <p className="section-label">Automation Rca Run</p>
          <h3 id="automation-run-heading">Automation Rca Run counts</h3>
        </div>
        <label className="summary-period">
          <span>Time period</span>
          <select value={period} onChange={(event) => setPeriod(event.target.value)} disabled={isLoading}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      </div>
      {error && <p className="message message--error summary-message" role="alert"><span aria-hidden="true">!</span>{error}</p>}
      {isLoading ? (
        <p className="empty-results">Loading {period} automation run counts...</p>
      ) : rows.length > 0 ? (
        <div className="results-table-wrap">
          <table className="results-table summary-table">
            <thead>
              <tr>
                <th scope="col">DATE</th>
                <th scope="col">Y</th>
                <th scope="col">N</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.period}>
                  <td>{row.period_label || row.period || '—'}</td>
                  <td>{row.Y_count ?? 0}</td>
                  <td>{row.N_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-results">No automation run count data was returned for this period.</p>
      )}
      {rows.length > 0 && (
        <div className="pagination-controls" aria-label="Automation run pagination">
          <label className="rows-per-page">
            Rows per page
            <select value={rowsPerPage} onChange={changeRowsPerPage}>
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>
          <span className="pagination-status">Showing {pageStartIndex + 1}-{Math.min(pageStartIndex + rowsPerPage, rows.length)} of {rows.length}</span>
          <div className="pagination-buttons">
            <button type="button" onClick={() => setCurrentPage((page) => page - 1)} disabled={currentPage === 1}>Previous</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button type="button" onClick={() => setCurrentPage((page) => page + 1)} disabled={currentPage === totalPages}>Next</button>
          </div>
        </div>
      )}
    </section>
  )
}

export default AutomationRunTable
