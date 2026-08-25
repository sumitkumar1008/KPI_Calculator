import { useRef, useState } from 'react'
import FileIcon from './FileIcon'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import './FileUpload.css'

function FileUpload() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [resultRows, setResultRows] = useState([])
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const resetUpload = () => {
    setSelectedFile(null)
    setError(null)
    setUploadStatus(null)
    setResultRows([])
    setCurrentPage(1)
    setIsUploading(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  const selectFile = (file) => {
    // Keep invalid files out of state so the upload action can only use valid input.
    const validationError = validateFile(file)
    setError(validationError)
    setUploadStatus(null)
    if (validationError) {
      setSelectedFile(null)
      if (inputRef.current) inputRef.current.value = ''
      return
    }
    setSelectedFile(file)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files?.[0])
  }

  const uploadFile = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setError(null)
    setUploadStatus(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      const response = await fetch(import.meta.env.VITE_API_ENDPOINT || '/api/v1/kpi/upload', {
        method: 'POST',
        body: formData,
      })

      const responseData = await response.json()
      if (!response.ok) {
        throw new Error(responseData.detail || responseData.message || 'The file could not be processed.')
      }

      setResultRows(Array.isArray(responseData.rows) ? responseData.rows : [])
      setCurrentPage(1)
      setUploadStatus('success')
    } catch (uploadError) {
      setError(uploadError.message || 'Something went wrong while uploading the file.')
      setUploadStatus(null)
    } finally {
      setIsUploading(false)
    }
  }

  const extension = selectedFile?.name.split('.').pop()?.toUpperCase()
  const hasSelectedFile = Boolean(selectedFile)
  const isSuccess = uploadStatus === 'success'
  const totalPages = Math.ceil(resultRows.length / rowsPerPage)
  const pageStartIndex = (currentPage - 1) * rowsPerPage
  const visibleRows = resultRows.slice(pageStartIndex, pageStartIndex + rowsPerPage)

  const changeRowsPerPage = (event) => {
    setRowsPerPage(Number(event.target.value))
    setCurrentPage(1)
  }

  return (
    <>
      <div className="section-intro">
        <p className="section-label">Step 01</p>
        <h2 id="upload-heading">Bring your data into focus</h2>
        <p>Select a spreadsheet to prepare it for KPI analysis.</p>
      </div>

      <div
        className={`upload-card ${isDragging ? 'is-dragging' : ''} ${hasSelectedFile ? 'has-file' : ''}`}
        onDragEnter={(event) => { event.preventDefault(); setIsDragging(true) }}
        onDragOver={(event) => { event.preventDefault(); setIsDragging(true) }}
        onDragLeave={(event) => { if (event.currentTarget === event.target) setIsDragging(false) }}
        onDrop={handleDrop}
      >
        <input ref={inputRef} id="file-input" type="file" accept=".csv,.xls,.xlsx" hidden onChange={(event) => selectFile(event.target.files?.[0])} />
        {hasSelectedFile ? (
          <div className="file-state">
            <div className="file-icon-wrap"><FileIcon /></div>
            <p className="file-name" title={selectedFile.name}>{selectedFile.name}</p>
            <p className="file-meta">{extension} <span aria-hidden="true">•</span> {formatFileSize(selectedFile.size)}</p>
            <button type="button" className="text-button" onClick={resetUpload}>Change file</button>
          </div>
        ) : (
          <div className="empty-state">
            <div className="upload-icon-wrap"><FileIcon compact /></div>
            <h3>Upload your file</h3>
            <p>Drag &amp; drop your file here</p>
            <span className="or-divider"><span>or</span></span>
            <label className="choose-button" htmlFor="file-input">Choose file</label>
            <p className="supported">Supported formats: CSV, XLS, XLSX</p>
          </div>
        )}
      </div>

      {error && <p className="message message--error" role="alert"><span aria-hidden="true">!</span>{error}</p>}
      {isSuccess && <p className="message message--success" role="status"><span aria-hidden="true">✓</span>File ready for processing</p>}

      <button className="upload-button" type="button" disabled={!hasSelectedFile || isUploading || isSuccess} onClick={uploadFile}>
        {isUploading ? 'Uploading...' : isSuccess ? 'File uploaded' : 'Upload file'}
        {!isUploading && !isSuccess && <span aria-hidden="true">→</span>}
      </button>
      {isSuccess && <button type="button" className="another-button" onClick={resetUpload}>Choose another file</button>}

      {isSuccess && (
        <section className="results-section" aria-labelledby="results-heading">
          <div className="results-heading">
            <p className="section-label">Step 02</p>
            <h2 id="results-heading">KPI results</h2>
          </div>
          {resultRows.length > 0 ? (
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
          {resultRows.length > 0 && (
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
              <span className="pagination-status">Showing {pageStartIndex + 1}-{Math.min(pageStartIndex + rowsPerPage, resultRows.length)} of {resultRows.length}</span>
              <div className="pagination-buttons">
                <button type="button" onClick={() => setCurrentPage((page) => page - 1)} disabled={currentPage === 1}>Previous</button>
                <span>Page {currentPage} of {totalPages}</span>
                <button type="button" onClick={() => setCurrentPage((page) => page + 1)} disabled={currentPage === totalPages}>Next</button>
              </div>
            </div>
          )}
        </section>
      )}
    </>
  )
}

export default FileUpload
