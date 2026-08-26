function ResultsTable({ rows, visibleRows, rowsPerPage, currentPage, totalPages, pageStartIndex, onRowsPerPageChange, onPrevious, onNext }) {
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
            <select value={rowsPerPage} onChange={onRowsPerPageChange}>
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>
          <span className="pagination-status">Showing {pageStartIndex + 1}-{Math.min(pageStartIndex + rowsPerPage, rows.length)} of {rows.length}</span>
          <div className="pagination-buttons">
            <button type="button" onClick={onPrevious} disabled={currentPage === 1}>Previous</button>
            <span>Page {currentPage} of {totalPages}</span>
            <button type="button" onClick={onNext} disabled={currentPage === totalPages}>Next</button>
          </div>
        </div>
      )}
    </>
  )
}

export default ResultsTable
