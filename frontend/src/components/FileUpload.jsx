import { useEffect, useRef, useState } from 'react'
import FileIcon from './FileIcon'
import ResultsTable from './MasterTable'
import AvgTable from './AvgTable'
import AutomationRunTable from './AutomationRunTable'
import AutomationRcaConclusionTable from './AutomationRcaConclusionTable'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import './FileUpload.css'

function FileUpload() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [resultRows, setResultRows] = useState([])
  const [uploadResponse, setUploadResponse] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const resetUpload = () => {
    setSelectedFile(null)
    setError(null)
    setUploadStatus(null)
    setResultRows([])
    setUploadResponse(null)
    setIsUploading(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  const selectFile = (file) => {
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
      const cleanText = text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
      const preview = cleanText ? cleanText.slice(0, 150) : (response.statusText || 'Server Error')
      throw new Error(`Server Error HTTP ${response.status}: ${preview}`)
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
          <AvgTable
            sourceResponse={uploadResponse}
          />
          <AutomationRunTable
            sourceResponse={uploadResponse}
          />
          <AutomationRcaConclusionTable
            sourceResponse={uploadResponse}
          />
          <div className="results-heading">
            <p className="section-label"></p>
            <h2 id="results-heading">KPI results</h2>
          </div>
          <ResultsTable
            rows={resultRows}
          />
        </section>
      )}
    </>
  )
}

export default FileUpload
