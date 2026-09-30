import { createContext, useContext, useState, useCallback } from 'react'
import { uploadNsttFiles, processNstt, getNsttDrilldown, exportNstt } from '../services/nsttApi'

const NsttContext = createContext(null)

export function NsttProvider({ children }) {
  const [namoFile, setNamoFile] = useState(null)
  const [remedyFile, setRemedyFile] = useState(null)
  const [uploadId, setUploadId] = useState(null)
  const [masterResponse, setMasterResponse] = useState(null)
  const [classifiedMasterResponse, setClassifiedMasterResponse] = useState(null)
  const [aggregatedResult, setAggregatedResult] = useState(null)
  const [stats, setStats] = useState(null)
  const [warnings, setWarnings] = useState([])

  // Pipeline execution state
  const [isProcessing, setIsProcessing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState(null)

  // Navigation and drilldown UI state
  const [drilldownCategory, setDrilldownCategory] = useState(null)
  const [drilldownData, setDrilldownData] = useState(null)
  const [isDrilldownLoading, setIsDrilldownLoading] = useState(false)
  const [isDrilldownOpen, setIsDrilldownOpen] = useState(false)

  /**
   * Main Pipeline Execution:
   * Coordinates file upload, backend VLOOKUP, Rule Engine classification, and Aggregation
   * Logs each step into console.log instead of UI visualization.
   */
  const processFiles = useCallback(async (customNamo = null, customRemedy = null) => {
    const file1 = customNamo || namoFile
    const file2 = customRemedy || remedyFile

    if (!file1 || !file2) {
      setError('Please select both Namo Report (Dataset 1) and Remedy Report (Dataset 2).')
      return
    }

    setIsProcessing(true)
    setError(null)
    setIsComplete(false)

    console.group('%c[NSTT Pipeline] Starting Processing Pipeline', 'color: #3b82f6; font-weight: bold; font-size: 13px;')
    console.log(`[Step 1/5] Namo file selected: ${file1.name} (${(file1.size / 1024).toFixed(1)} KB)`)
    console.log(`[Step 2/5] Remedy file selected: ${file2.name} (${(file2.size / 1024).toFixed(1)} KB)`)

    try {
      // Step 3: Column validation, VLOOKUP join, impact conversion & Master Response generation
      console.log('[Step 3/5] Uploading files, validating required columns & executing VLOOKUP join...')
      const uploadResult = await uploadNsttFiles(file1, file2)

      console.log('[Step 3/5] VLOOKUP Join complete! Ingestion stats:', uploadResult.stats)
      if (uploadResult.warnings?.length > 0) {
        console.warn('[Step 3/5] Ingestion warnings:', uploadResult.warnings)
      }

      setUploadId(uploadResult.upload_id)
      setMasterResponse(uploadResult.master_response)
      setStats(uploadResult.stats)
      setWarnings(uploadResult.warnings || [])

      // Step 4 & 5: Rule Engine classification & hierarchical dashboard aggregation
      console.log('[Step 4/5] Executing NSTT Rule Engine business classification...')
      console.log('[Step 5/5] Computing hierarchical dashboard aggregations...')

      const processResult = await processNstt({
        uploadId: uploadResult.upload_id,
        masterResponse: uploadResult.master_response,
      })

      console.log('[Step 5/5] Aggregation complete! Total SR:', processResult.aggregated_result?.total_sr, '| NSTT Count:', processResult.aggregated_result?.nstt_count)
      console.log('%c[NSTT Pipeline] Complete! Successfully generated dashboard metrics.', 'color: #10b981; font-weight: bold;')
      console.groupEnd()

      setClassifiedMasterResponse(processResult.classified_master_response)
      setAggregatedResult(processResult.aggregated_result)
      setIsComplete(true)
    } catch (err) {
      const errMsg = err.message || 'An unexpected error occurred during processing.'
      console.error('%c[NSTT Pipeline Error]', 'color: #ef4444; font-weight: bold;', errMsg)
      console.groupEnd()
      setError(errMsg)
    } finally {
      setIsProcessing(false)
    }
  }, [namoFile, remedyFile])

  /**
   * Drill-down handler for clickable counts in the dashboard
   */
  const openDrilldown = useCallback(async (category) => {
    if (!category) return
    setDrilldownCategory(category)
    setIsDrilldownOpen(true)
    setIsDrilldownLoading(true)

    try {
      const result = await getNsttDrilldown({
        category,
        uploadId,
        records: classifiedMasterResponse?.records,
      })
      setDrilldownData(result)
    } catch (err) {
      console.error('Drilldown query failed:', err)
      setDrilldownData({ category, total_records: 0, records: [], error: err.message })
    } finally {
      setIsDrilldownLoading(false)
    }
  }, [uploadId, classifiedMasterResponse])

  const closeDrilldown = () => {
    setIsDrilldownOpen(false)
    setDrilldownCategory(null)
    setDrilldownData(null)
  }

  /**
   * Reset the whole module state back to initial upload screen
   */
  const reset = useCallback(() => {
    setNamoFile(null)
    setRemedyFile(null)
    setUploadId(null)
    setMasterResponse(null)
    setClassifiedMasterResponse(null)
    setAggregatedResult(null)
    setStats(null)
    setWarnings([])
    setIsProcessing(false)
    setIsComplete(false)
    setError(null)
    closeDrilldown()
  }, [])

  /**
   * Excel export trigger
   */
  const handleExport = useCallback(async () => {
    try {
      await exportNstt({
        uploadId,
        masterResponse: classifiedMasterResponse || masterResponse,
      })
    } catch (err) {
      alert(`Export failed: ${err.message}`)
    }
  }, [uploadId, classifiedMasterResponse, masterResponse])

  return (
    <NsttContext.Provider
      value={{
        namoFile,
        setNamoFile,
        remedyFile,
        setRemedyFile,
        uploadId,
        masterResponse,
        classifiedMasterResponse,
        aggregatedResult,
        stats,
        warnings,
        isProcessing,
        isComplete,
        error,
        drilldownCategory,
        drilldownData,
        isDrilldownLoading,
        isDrilldownOpen,
        openDrilldown,
        closeDrilldown,
        processFiles,
        reset,
        handleExport,
      }}
    >
      {children}
    </NsttContext.Provider>
  )
}

export function useNstt() {
  const context = useContext(NsttContext)
  if (!context) {
    throw new Error('useNstt must be used within an NsttProvider')
  }
  return context
}
