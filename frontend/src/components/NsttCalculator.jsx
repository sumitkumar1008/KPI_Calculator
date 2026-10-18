import { useRef, useState } from 'react'
import FileIcon from './FileIcon'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import { useNstt } from '../context/NsttContext'
import NsttDashboard from './nstt/NsttDashboard'
import './NsttCalculator.css'

function NsttCalculator({ fileFormat = 'all' }) {
  const {
    namoFile,
    setNamoFile,
    remedyFile,
    setRemedyFile,
    isProcessing,
    isComplete,
    error,
    aggregatedResult,
    processFiles,
    reset,
  } = useNstt()

  const [isDragging1, setIsDragging1] = useState(false)
  const [isDragging2, setIsDragging2] = useState(false)
  const [localError1, setLocalError1] = useState(null)
  const [localError2, setLocalError2] = useState(null)

  const inputRef1 = useRef(null)
  const inputRef2 = useRef(null)

  const acceptedFormats = fileFormat === 'all' ? '.csv,.xls,.xlsx,.zip' : `.${fileFormat}`

  const selectFile1 = (file) => {
    if (!file) return
    const validationError = validateFile(file)
    setLocalError1(validationError)
    if (validationError) {
      setNamoFile(null)
      if (inputRef1.current) inputRef1.current.value = ''
      return
    }
    setNamoFile(file)
  }

  const selectFile2 = (file) => {
    if (!file) return
    const validationError = validateFile(file)
    setLocalError2(validationError)
    if (validationError) {
      setRemedyFile(null)
      if (inputRef2.current) inputRef2.current.value = ''
      return
    }
    setRemedyFile(file)
  }

  const resetFile1 = () => {
    setNamoFile(null)
    setLocalError1(null)
    if (inputRef1.current) inputRef1.current.value = ''
  }

  const resetFile2 = () => {
    setRemedyFile(null)
    setLocalError2(null)
    if (inputRef2.current) inputRef2.current.value = ''
  }

  const handleCalculate = async () => {
    if (!namoFile || !remedyFile || isProcessing) return
    await processFiles(namoFile, remedyFile)
  }

  // If calculation is complete and results are present, render the dashboard
  if (isComplete && aggregatedResult) {
    return <NsttDashboard />
  }

  const ext1 = namoFile?.name.split('.').pop()?.toUpperCase()
  const ext2 = remedyFile?.name.split('.').pop()?.toUpperCase()

  const errorMessage = typeof error === 'string' ? error : (error?.message || '')
  const errorType = error?.errorType || ''
  const isFileMismatch =
    errorType === 'FILE_MISMATCH' ||
    (Array.isArray(error?.missingColumns) && error.missingColumns.length > 0) ||
    errorMessage.toLowerCase().includes('file mismatch') ||
    errorMessage.toLowerCase().includes('missing required column') ||
    errorMessage.toLowerCase().includes('column validation failed')
  const missingCols = Array.isArray(error?.missingColumns) ? error.missingColumns : []
  const filesDetail = error?.files || null
  const errorDataset = error?.dataset || (typeof error === 'string' ? error : '')

  const isDataset1Error = Boolean(
    (filesDetail?.file1?.status === 'mismatch' || filesDetail?.file1?.status === 'unparseable') ||
    (!filesDetail && error && (
      errorDataset.includes('Dataset 01') ||
      errorDataset.includes('Dataset 1') ||
      errorMessage.includes('Dataset 01') ||
      errorMessage.includes('Dataset 1') ||
      errorMessage.includes('Namo') ||
      errorMessage.includes('File 1')
    ))
  )

  const isDataset2Error = Boolean(
    (filesDetail?.file2?.status === 'mismatch' || filesDetail?.file2?.status === 'unparseable') ||
    (!filesDetail && error && (
      errorDataset.includes('Dataset 02') ||
      errorDataset.includes('Dataset 2') ||
      errorMessage.includes('Dataset 02') ||
      errorMessage.includes('Dataset 2') ||
      errorMessage.includes('Remedy') ||
      errorMessage.includes('File 2')
    ))
  )

  return (
    <section className="nstt-section" aria-labelledby="nstt-heading">
      <div className="section-intro">
        <p className="section-label">NSTT Analysis Module</p>
        <h2 id="nstt-heading">NSTT Calculator</h2>
        <p>Upload both datasets below to correlate and calculate Network Service Turnaround Times (NSTT).</p>
      </div>

      {error && (
        <div className="nstt-error-banner" role="alert">
          <div className="nstt-error-header">
            <span className="nstt-error-icon" aria-hidden="true">⚠️</span>
            <div className="nstt-error-body">
              <div className="nstt-error-title-row">
                <h4 className="nstt-error-title">
                  {isFileMismatch ? 'File Mismatch Error' : 'File Validation / Upload Error'}
                </h4>
                {error?.dataset && (
                  <span className="nstt-error-dataset-tag">{error.dataset}</span>
                )}
              </div>
              <p className="nstt-error-msg">
                {isFileMismatch
                  ? 'Required column mismatch detected. Please check the missing columns below:'
                  : errorMessage}
              </p>

              {filesDetail ? (
                <div className="nstt-files-validation-grid">
                  {filesDetail.file1?.missing_columns?.length > 0 && (
                    <div className="nstt-missing-cols-panel">
                      <div className="nstt-missing-cols-header">
                        <span className="nstt-missing-cols-label">
                          {filesDetail.file1.slot || 'Dataset 01'} ({filesDetail.file1.target_dataset}):
                        </span>
                        <span className="nstt-missing-cols-hint">
                          {filesDetail.file1.missing_columns.length} missing column(s)
                        </span>
                      </div>
                      <div className="nstt-missing-chips-list">
                        {filesDetail.file1.missing_columns.map((col, idx) => (
                          <span key={idx} className="nstt-missing-chip" title={`Missing required column: ${col}`}>
                            <span className="nstt-missing-chip-x" aria-hidden="true">✕</span>
                            <code>{col}</code>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {filesDetail.file2?.missing_columns?.length > 0 && (
                    <div className="nstt-missing-cols-panel">
                      <div className="nstt-missing-cols-header">
                        <span className="nstt-missing-cols-label">
                          {filesDetail.file2.slot || 'Dataset 02'} ({filesDetail.file2.target_dataset}):
                        </span>
                        <span className="nstt-missing-cols-hint">
                          {filesDetail.file2.missing_columns.length} missing column(s)
                        </span>
                      </div>
                      <div className="nstt-missing-chips-list">
                        {filesDetail.file2.missing_columns.map((col, idx) => (
                          <span key={idx} className="nstt-missing-chip" title={`Missing required column: ${col}`}>
                            <span className="nstt-missing-chip-x" aria-hidden="true">✕</span>
                            <code>{col}</code>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                missingCols.length > 0 && (
                  <div className="nstt-missing-cols-panel">
                    <div className="nstt-missing-cols-header">
                      <span className="nstt-missing-cols-label">Missing Columns ({missingCols.length}):</span>
                      <span className="nstt-missing-cols-hint">The following required columns were not found in this file:</span>
                    </div>
                    <div className="nstt-missing-chips-list">
                      {missingCols.map((col, idx) => (
                        <span key={idx} className="nstt-missing-chip" title={`Missing required column: ${col}`}>
                          <span className="nstt-missing-chip-x" aria-hidden="true">✕</span>
                          <code>{col}</code>
                        </span>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
          <div className="nstt-error-actions">
            <button type="button" className="nstt-error-dismiss" onClick={reset}>
              Clear &amp; Try Again
            </button>
          </div>
        </div>
      )}

      <div className="nstt-upload-grid">
        {/* Upload Box 1 - Namo Report */}
        <div className="nstt-upload-col">
          <div className="nstt-box-header">
            <span className="nstt-badge">Dataset 01</span>
            <h3>Namo Report (Primary Data)</h3>
          </div>
          <div
            className={`upload-card nstt-upload-card ${isDragging1 ? 'is-dragging' : ''} ${namoFile ? 'has-file' : ''} ${isDataset1Error ? 'has-card-error' : ''}`}
            onDragEnter={(e) => { e.preventDefault(); setIsDragging1(true) }}
            onDragOver={(e) => { e.preventDefault(); setIsDragging1(true) }}
            onDragLeave={(e) => { if (e.currentTarget === e.target) setIsDragging1(false) }}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragging1(false)
              selectFile1(e.dataTransfer.files?.[0])
            }}
          >
            <input
              ref={inputRef1}
              id="nstt-file-input-1"
              type="file"
              accept={acceptedFormats}
              hidden
              onChange={(e) => selectFile1(e.target.files?.[0])}
            />

            {namoFile ? (
              <div className="file-state">
                <div className="file-icon-wrap"><FileIcon /></div>
                <p className="file-name" title={namoFile.name}>{namoFile.name}</p>
                <p className="file-meta">{ext1} <span aria-hidden="true">•</span> {formatFileSize(namoFile.size)}</p>
                <button type="button" className="text-button" onClick={resetFile1}>Change file</button>
              </div>
            ) : (
              <div className="empty-state">
                <div className="upload-icon-wrap"><FileIcon compact /></div>
                <h3>Upload Namo Report</h3>
                <p>Drag &amp; drop file here</p>
                <span className="or-divider"><span>or</span></span>
                <label className="choose-button" htmlFor="nstt-file-input-1">Choose file</label>
              </div>
            )}
          </div>
          {localError1 && <p className="message message--error" role="alert"><span aria-hidden="true">!</span>{localError1}</p>}
        </div>

        {/* Upload Box 2 - Remedy Report */}
        <div className="nstt-upload-col">
          <div className="nstt-box-header">
            <span className="nstt-badge">Dataset 02</span>
            <h3>Remedy Report (Secondary Data)</h3>
          </div>
          <div
            className={`upload-card nstt-upload-card ${isDragging2 ? 'is-dragging' : ''} ${remedyFile ? 'has-file' : ''} ${isDataset2Error ? 'has-card-error' : ''}`}
            onDragEnter={(e) => { e.preventDefault(); setIsDragging2(true) }}
            onDragOver={(e) => { e.preventDefault(); setIsDragging2(true) }}
            onDragLeave={(e) => { if (e.currentTarget === e.target) setIsDragging2(false) }}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragging2(false)
              selectFile2(e.dataTransfer.files?.[0])
            }}
          >
            <input
              ref={inputRef2}
              id="nstt-file-input-2"
              type="file"
              accept={acceptedFormats}
              hidden
              onChange={(e) => selectFile2(e.target.files?.[0])}
            />

            {remedyFile ? (
              <div className="file-state">
                <div className="file-icon-wrap"><FileIcon /></div>
                <p className="file-name" title={remedyFile.name}>{remedyFile.name}</p>
                <p className="file-meta">{ext2} <span aria-hidden="true">•</span> {formatFileSize(remedyFile.size)}</p>
                <button type="button" className="text-button" onClick={resetFile2}>Change file</button>
              </div>
            ) : (
              <div className="empty-state">
                <div className="upload-icon-wrap"><FileIcon compact /></div>
                <h3>Upload Remedy Report</h3>
                <p>Drag &amp; drop file here</p>
                <span className="or-divider"><span>or</span></span>
                <label className="choose-button" htmlFor="nstt-file-input-2">Choose file</label>
              </div>
            )}
          </div>
          {localError2 && <p className="message message--error" role="alert"><span aria-hidden="true">!</span>{localError2}</p>}
        </div>
      </div>

        <div className="nstt-actions">
          <button
            className="upload-button"
            type="button"
            disabled={!namoFile || !remedyFile || isProcessing}
            onClick={handleCalculate}
          >
            {isProcessing ? 'Processing NSTT Calculation...' : 'Calculate NSTT'}
            {!isProcessing && <span aria-hidden="true">→</span>}
          </button>

          {(namoFile || remedyFile) && !isProcessing && (
            <button type="button" className="another-button" onClick={reset}>
              Clear both files
            </button>
          )}
        </div>
      </section>
  )
}

export default NsttCalculator
