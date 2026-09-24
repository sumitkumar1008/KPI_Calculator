import { useRef, useState } from 'react'
import FileIcon from './FileIcon'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import './NsttCalculator.css'

function NsttCalculator({ fileFormat = 'all' }) {
  const [file1, setFile1] = useState(null)
  const [file2, setFile2] = useState(null)
  const [isDragging1, setIsDragging1] = useState(false)
  const [isDragging2, setIsDragging2] = useState(false)
  const [error1, setError1] = useState(null)
  const [error2, setError2] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState(null)

  const inputRef1 = useRef(null)
  const inputRef2 = useRef(null)

  const acceptedFormats = fileFormat === 'all' ? '.csv,.xls,.xlsx,.zip' : `.${fileFormat}`

  const selectFile1 = (file) => {
    const validationError = validateFile(file)
    setError1(validationError)
    setStatusMessage(null)
    if (validationError) {
      setFile1(null)
      if (inputRef1.current) inputRef1.current.value = ''
      return
    }
    setFile1(file)
  }

  const selectFile2 = (file) => {
    const validationError = validateFile(file)
    setError2(validationError)
    setStatusMessage(null)
    if (validationError) {
      setFile2(null)
      if (inputRef2.current) inputRef2.current.value = ''
      return
    }
    setFile2(file)
  }

  const resetFile1 = () => {
    setFile1(null)
    setError1(null)
    setStatusMessage(null)
    if (inputRef1.current) inputRef1.current.value = ''
  }

  const resetFile2 = () => {
    setFile2(null)
    setError2(null)
    setStatusMessage(null)
    if (inputRef2.current) inputRef2.current.value = ''
  }

  const resetAll = () => {
    resetFile1()
    resetFile2()
    setIsProcessing(false)
    setStatusMessage(null)
  }

  const handleCalculate = async () => {
    if (!file1 || !file2) return

    setIsProcessing(true)
    setStatusMessage(null)

    // Simulate calculation / prepare for future backend API
    try {
      await new Promise((resolve) => setTimeout(resolve, 800))
      setStatusMessage({
        type: 'success',
        text: `Both datasets (${file1.name} & ${file2.name}) are loaded and ready for NSTT analysis.`,
      })
    } catch {
      setStatusMessage({
        type: 'error',
        text: 'Something went wrong while processing the NSTT datasets.',
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const ext1 = file1?.name.split('.').pop()?.toUpperCase()
  const ext2 = file2?.name.split('.').pop()?.toUpperCase()

  return (
    <section className="nstt-section" aria-labelledby="nstt-heading">
      <div className="section-intro">
        <p className="section-label">NSTT Analysis Module</p>
        <h2 id="nstt-heading">NSTT Calculator</h2>
        <p>Upload both datasets below to correlate and calculate Network Service Turnaround Times (NSTT).</p>
      </div>

      <div className="nstt-upload-grid">
        {/* Upload Box 1 */}
        <div className="nstt-upload-col">
          <div className="nstt-box-header">
            <span className="nstt-badge">Dataset 01</span>
            <h3>Primary Data File</h3>
          </div>
          <div
            className={`upload-card nstt-upload-card ${isDragging1 ? 'is-dragging' : ''} ${file1 ? 'has-file' : ''}`}
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

            {file1 ? (
              <div className="file-state">
                <div className="file-icon-wrap"><FileIcon /></div>
                <p className="file-name" title={file1.name}>{file1.name}</p>
                <p className="file-meta">{ext1} <span aria-hidden="true">•</span> {formatFileSize(file1.size)}</p>
                <button type="button" className="text-button" onClick={resetFile1}>Change file</button>
              </div>
            ) : (
              <div className="empty-state">
                <div className="upload-icon-wrap"><FileIcon compact /></div>
                <h3>Upload Dataset 1</h3>
                <p>Drag &amp; drop file here</p>
                <span className="or-divider"><span>or</span></span>
                <label className="choose-button" htmlFor="nstt-file-input-1">Choose file</label>
                <p className="supported">Supported formats: CSV, XLS, XLSX, ZIP</p>
              </div>
            )}
          </div>
          {error1 && <p className="message message--error" role="alert"><span aria-hidden="true">!</span>{error1}</p>}
        </div>

        {/* Upload Box 2 */}
        <div className="nstt-upload-col">
          <div className="nstt-box-header">
            <span className="nstt-badge">Dataset 02</span>
            <h3>Secondary Data File</h3>
          </div>
          <div
            className={`upload-card nstt-upload-card ${isDragging2 ? 'is-dragging' : ''} ${file2 ? 'has-file' : ''}`}
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

            {file2 ? (
              <div className="file-state">
                <div className="file-icon-wrap"><FileIcon /></div>
                <p className="file-name" title={file2.name}>{file2.name}</p>
                <p className="file-meta">{ext2} <span aria-hidden="true">•</span> {formatFileSize(file2.size)}</p>
                <button type="button" className="text-button" onClick={resetFile2}>Change file</button>
              </div>
            ) : (
              <div className="empty-state">
                <div className="upload-icon-wrap"><FileIcon compact /></div>
                <h3>Upload Dataset 2</h3>
                <p>Drag &amp; drop file here</p>
                <span className="or-divider"><span>or</span></span>
                <label className="choose-button" htmlFor="nstt-file-input-2">Choose file</label>
                <p className="supported">Supported formats: CSV, XLS, XLSX, ZIP</p>
              </div>
            )}
          </div>
          {error2 && <p className="message message--error" role="alert"><span aria-hidden="true">!</span>{error2}</p>}
        </div>
      </div>

      {statusMessage && (
        <p className={`message message--${statusMessage.type}`} role="status">
          <span aria-hidden="true">{statusMessage.type === 'success' ? '✓' : '!'}</span>
          {statusMessage.text}
        </p>
      )}

      <div className="nstt-actions">
        <button
          className="upload-button"
          type="button"
          disabled={!file1 || !file2 || isProcessing}
          onClick={handleCalculate}
        >
          {isProcessing ? 'Calculating NSTT...' : 'Calculate NSTT'}
          {!isProcessing && <span aria-hidden="true">→</span>}
        </button>

        {(file1 || file2) && (
          <button type="button" className="another-button" onClick={resetAll}>
            Clear both files
          </button>
        )}
      </div>
    </section>
  )
}

export default NsttCalculator
