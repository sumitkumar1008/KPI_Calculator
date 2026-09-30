import { useRef, useState } from 'react'
import FileIcon from './FileIcon'
import { formatFileSize, validateFile } from '../utils/fileValidation'
import { useNstt } from '../context/NsttContext'
import ProcessingStatus from './nstt/ProcessingStatus'
import NsttDashboard from './nstt/NsttDashboard'
import './NsttCalculator.css'

function NsttCalculator({ fileFormat = 'all' }) {
  const {
    namoFile,
    setNamoFile,
    remedyFile,
    setRemedyFile,
    isProcessing,
    currentStep,
    stepStates,
    isComplete,
    error,
    aggregatedResult,
    stats,
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

  return (
    <section className="nstt-section" aria-labelledby="nstt-heading">
      <div className="section-intro">
        <p className="section-label">NSTT Analysis Module</p>
        <h2 id="nstt-heading">NSTT Calculator</h2>
        <p>Upload both datasets below to correlate and calculate Network Service Turnaround Times (NSTT).</p>
      </div>

      {/* Processing Pipeline Status Indicator */}
      {(isProcessing || error) && (
        <ProcessingStatus
          currentStep={currentStep}
          stepStates={stepStates}
          isComplete={isComplete}
          hasError={Boolean(error)}
          errorMessage={error}
          namoFileName={namoFile?.name}
          remedyFileName={remedyFile?.name}
          stats={stats}
          onReset={reset}
        />
      )}

      {!isProcessing && (
        <>
          <div className="nstt-upload-grid">
            {/* Upload Box 1 - Namo Report */}
            <div className="nstt-upload-col">
              <div className="nstt-box-header">
                <span className="nstt-badge">Dataset 01</span>
                <h3>Namo Report (Primary Data)</h3>
              </div>
              <div
                className={`upload-card nstt-upload-card ${isDragging1 ? 'is-dragging' : ''} ${namoFile ? 'has-file' : ''}`}
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
                    <p className="supported">Required: INCIDENTID, ATTRIBUTEDTO, SRCREATIONTIME...</p>
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
                className={`upload-card nstt-upload-card ${isDragging2 ? 'is-dragging' : ''} ${remedyFile ? 'has-file' : ''}`}
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
                    <p className="supported">Required: INCIDENT_NUMBER, UP_TIME, INCIDENT_IMPACT...</p>
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
              {isProcessing ? 'Processing Pipeline...' : 'Calculate NSTT'}
              {!isProcessing && <span aria-hidden="true">→</span>}
            </button>

            {(namoFile || remedyFile) && (
              <button type="button" className="another-button" onClick={reset}>
                Clear both files
              </button>
            )}
          </div>
        </>
      )}
    </section>
  )
}

export default NsttCalculator
