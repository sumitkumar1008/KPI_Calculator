import { useRef, useState } from 'react'
import FileIcon from './FileIcon'
import ResultsTable from './MasterTable'
import AvgTable from './AvgTable'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import './FileUpload.css'

function FileUpload() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [resultRows, setResultRows] = useState([])
  const [uploadResponse, setUploadResponse] = useState(null)
  const [summaryRows, setSummaryRows] = useState([])
  const [summaryPeriod, setSummaryPeriod] = useState('daily')
  const [isSummaryLoading, setIsSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState(null)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const resetUpload = () => {
    setSelectedFile(null)
    setError(null)
    setUploadStatus(null)
    setResultRows([])
    setUploadResponse(null)
    setSummaryRows([])
    setSummaryPeriod('daily')
    setSummaryError(null)
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

  const safeParseJson = async (response) => {
    const text = await response.text()
    let data = null
    try {
      data = JSON.parse(text)
    } catch {
      if (!response.ok) {
        throw new Error(`Server error HTTP ${response.status} (${response.statusText || 'Error'}). Please check backend service logs.`)
      }
      throw new Error('Server returned an invalid non-JSON response.')
    }

    if (!response.ok) {
      const serverMsg = data?.error || data?.detail || data?.message || `Server error HTTP ${response.status}.`
      throw new Error(serverMsg)
    }
    return data
  }

  const uploadFile = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setError(null)
    setUploadStatus(null)
    setSummaryError(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      const response = await fetch(import.meta.env.VITE_API_ENDPOINT || '/api/v1/kpi/upload', {
        method: 'POST',
        body: formData,
      })

      const responseData = await safeParseJson(response)
      if (!response.ok) {
        throw new Error(responseData.error || responseData.detail || responseData.message || 'The file could not be processed.')
      }

      setResultRows(Array.isArray(responseData.rows) ? responseData.rows : [])
      setUploadResponse(responseData)
      setCurrentPage(1)
      setUploadStatus('success')
      await loadSummary(responseData, summaryPeriod)
    } catch (uploadError) {
      setError(uploadError.message || 'Something went wrong while uploading the file.')
      setUploadStatus(null)
    } finally {
      setIsUploading(false)
    }
  }

  const loadSummary = async (sourceResponse, period) => {
    setIsSummaryLoading(true)
    setSummaryError(null)

    try {
      const endpoint = new URL(import.meta.env.VITE_SUMMARY_API_ENDPOINT || '/api/v1/kpi/summary?group_by=monthly', window.location.origin)
      endpoint.searchParams.set('group_by', period)
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sourceResponse),
      })
      const responseData = await safeParseJson(response)
      if (!response.ok) {
        throw new Error(responseData.error || responseData.detail || responseData.message || 'The summary could not be loaded.')
      }
      setSummaryRows(Array.isArray(responseData.summary) ? responseData.summary : [])
      if (!Array.isArray(responseData.summary)) {
        throw new Error(`The summary API returned no summary array for group_by=${period}.`)
      }
    } catch (summaryLoadError) {
      setSummaryRows([])
      setSummaryError(summaryLoadError.message || 'Something went wrong while loading the summary.')
    } finally {
      setIsSummaryLoading(false)
    }
  }

  const changeSummaryPeriod = async (event) => {
    const nextPeriod = event.target.value
    setSummaryPeriod(nextPeriod)
    await loadSummary(uploadResponse, nextPeriod)
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
          <ResultsTable
            rows={resultRows}
            visibleRows={visibleRows}
            rowsPerPage={rowsPerPage}
            currentPage={currentPage}
            totalPages={totalPages}
            pageStartIndex={pageStartIndex}
            onRowsPerPageChange={changeRowsPerPage}
            onPrevious={() => setCurrentPage((page) => page - 1)}
            onNext={() => setCurrentPage((page) => page + 1)}
          />
          <AvgTable
            rows={summaryRows}
            period={summaryPeriod}
            isLoading={isSummaryLoading}
            error={summaryError}
            onPeriodChange={changeSummaryPeriod}
          />
        </section>
      )}
    </>
  )
}

export default FileUpload
