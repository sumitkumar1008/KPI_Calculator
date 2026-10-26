import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import { uploadNsttFiles, processNstt, getNsttDrilldown, exportNstt } from '../services/nsttApi'
import { findBifurcationsForQuery } from '../utils/nsttBifurcationLocator'

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

  // Bifurcation Locator search & blinking state
  const [bifurcationQuery, setBifurcationQuery] = useState('')

  const bifurcationResult = useMemo(() => {
    const q = bifurcationQuery.trim()
    if (!q) return null
    const records = classifiedMasterResponse?.records || masterResponse?.records || []
    return findBifurcationsForQuery(records, q)
  }, [bifurcationQuery, classifiedMasterResponse, masterResponse])

  const highlightedBifurcationKeys = useMemo(() => {
    if (!bifurcationResult?.allKeys) return new Set()
    return new Set(bifurcationResult.allKeys)
  }, [bifurcationResult])

  const highlightedRowKeys = useMemo(() => {
    if (!bifurcationResult?.allRowKeys) return new Set()
    return new Set(bifurcationResult.allRowKeys)
  }, [bifurcationResult])

  /**
   * Main Pipeline Execution:
   * Coordinates file upload, backend VLOOKUP, Rule Engine classification, and Aggregation
   * Logs each step into console.log instead of UI visualization.
   */
  const processFiles = useCallback(async (customNamo = null, customRemedy = null) => {
    const file1 = customNamo || namoFile
    const file2 = customRemedy || remedyFile

    if (!file1 || !file2) {
      setError({
        message: 'Please select both Namo Report (Dataset 1) and Remedy Report (Dataset 2).',
        errorType: 'VALIDATION_ERROR',
        missingColumns: [],
      })
      return
    }

    setIsProcessing(true)
    setError(null)
    setIsComplete(false)

    const t0Client = performance.now()

    console.group('%c⏱️ [NSTT Performance Counter] Pipeline Execution Started', 'color: #3b82f6; font-weight: bold; font-size: 13px;')
    console.log(`[Start] Namo file: ${file1.name} (${(file1.size / 1024).toFixed(1)} KB) | Remedy file: ${file2.name} (${(file2.size / 1024).toFixed(1)} KB)`)

    try {
      // Phase 1: Upload (Validation, VLOOKUP, Impact Mapping, Master JSON)
      const tUploadStart = performance.now()
      console.log('🔄 [Upload Phase] Uploading datasets, running header validation & VLOOKUP join...')
      const uploadResult = await uploadNsttFiles(file1, file2)
      const tUploadEnd = performance.now()
      const clientUploadMs = Math.round(tUploadEnd - tUploadStart)

      const uBreak = uploadResult?.stats?.perf_breakdown || {}
      console.log(
        `✅ [Upload Phase Complete] Network + Server: ${clientUploadMs} ms | Server Perf Counter: ${uploadResult.stats?.processing_time_ms} ms\n` +
        `   ├─ 1. Validation & Reading: ${uBreak.file_validation_ms || '—'} ms\n` +
        `   ├─ 2. VLOOKUP Left-Join:    ${uBreak.vlookup_join_ms || '—'} ms\n` +
        `   ├─ 3. Impact & Duplicates:  ${uBreak.impact_and_duplicate_ms || '—'} ms\n` +
        `   ├─ 4. Master Response:      ${uBreak.master_builder_ms || '—'} ms\n` +
        `   └─ 5. Cache Storage:        ${uBreak.cache_store_ms || '—'} ms`
      )

      if (uploadResult.warnings?.length > 0) {
        console.warn('⚠️ [Upload Warnings]:', uploadResult.warnings)
      }

      setUploadId(uploadResult.upload_id)
      setMasterResponse(uploadResult.master_response)
      setStats(uploadResult.stats)
      setWarnings(uploadResult.warnings || [])

      // Phase 2: Process (Rule Engine, Hierarchical Aggregator, Cache Sync)
      const tProcStart = performance.now()
      console.log('🔄 [Process Phase] Executing Rule Engine classification & hierarchical aggregations...')

      const processResult = await processNstt({
        uploadId: uploadResult.upload_id,
        masterResponse: uploadResult.master_response,
      })
      const tProcEnd = performance.now()
      const clientProcMs = Math.round(tProcEnd - tProcStart)

      const pBreak = processResult?.perf_breakdown || {}
      const combinedStats = {
        ...uploadResult.stats,
        ...(processResult.stats || {}),
        perf_breakdown: {
          ...(uploadResult.stats?.perf_breakdown || {}),
          ...pBreak,
          client_total_ms: Math.round(performance.now() - t0Client),
        },
      }

      console.log(
        `✅ [Process Phase Complete] Network + Server: ${clientProcMs} ms | Server Perf Counter: ${processResult.processing_time_ms} ms\n` +
        `   ├─ 1. Rule Engine Classification: ${pBreak.rule_engine_ms || '—'} ms\n` +
        `   ├─ 2. Hierarchical Aggregation:   ${pBreak.aggregation_ms || '—'} ms\n` +
        `   └─ 3. Cache Sync & Final Output:  ${pBreak.cache_sync_ms || '—'} ms`
      )

      const totalMs = Math.round(performance.now() - t0Client)
      console.log(
        `%c🏁 [Final Output Delivered] Total End-to-End Elapsed Time: ${totalMs} ms (${(totalMs / 1000).toFixed(3)} s) | Total Records: ${processResult.aggregated_result?.total_sr || 0} | NSTT Count: ${processResult.aggregated_result?.nstt_count || 0}`,
        'color: #10b981; font-weight: bold; font-size: 13px;'
      )
      console.groupEnd()

      setStats(combinedStats)
      setClassifiedMasterResponse(processResult.classified_master_response)
      setAggregatedResult(processResult.aggregated_result)
      setIsComplete(true)
    } catch (err) {
      const errMsg = err.message || 'An unexpected error occurred during processing.'
      console.error(
        '%c[NSTT File Mismatch / Pipeline Error]',
        'color: #ef4444; font-weight: bold; font-size: 13px;',
        '\nMessage:', errMsg,
        '\nMissing Columns:', err.missingColumns || [],
        '\nDataset:', err.dataset || 'N/A',
        '\nInternal Error Details:\n', err.internalError || errMsg
      )
      console.groupEnd()
      setError({
        message: errMsg,
        errorType: err.errorType || 'ERROR',
        dataset: err.dataset || null,
        filename: err.filename || null,
        missingColumns: err.missingColumns || [],
        foundColumns: err.foundColumns || [],
        expectedColumns: err.expectedColumns || [],
        files: err.files || null,
        internalError: err.internalError || errMsg,
      })
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
    setBifurcationQuery('')
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
        bifurcationQuery,
        setBifurcationQuery,
        bifurcationResult,
        highlightedBifurcationKeys,
        highlightedRowKeys,
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
