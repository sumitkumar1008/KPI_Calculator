import { useEffect, useState } from 'react'

function ResultsTable({ rows }) {
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage))
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = rows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  useEffect(() => {
    setCurrentPage(1)
  }, [rows])

  const changeRowsPerPage = (event) => {
    setRowsPerPage(Number(event.target.value))
    setCurrentPage(1)
  }

  return (
    <>
      {rows.length > 0 ? (
        <div className="results-table-wrap">
          <table className="results-table">
            <thead>
              <tr>
                <th scope="col">SRNUMBER</th>
                <th scope="col">MTTI</th>
                <th scope="col">MTTA</th>
                <th scope="col">MTTAck</th>
                <th scope="col">MTTR</th>
                <th scope="col">MTTr</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row, index) => (
                <tr key={`${row.SRNUMBER || 'row'}-${pageStartIndex + index}`}>
                  <td>{row.SRNUMBER || '—'}</td>
                  <td>{row.MTTI || '—'}</td>
                  <td>{row.MTTA || '—'}</td>
                  <td>{row.MTTAck || '—'}</td>
                  <td>{row.MTTR || '—'}</td>
                  <td>{row.MTTr || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-results">The response did not contain any result rows.</p>
      )}
      {rows.length > 0 && (
        <div className="pagination-controls" aria-label="Table pagination">
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
    </>
  )
}

export default ResultsTable
