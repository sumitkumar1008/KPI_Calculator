import { createContext, useContext, useState, useCallback } from 'react'
import { uploadNsttFiles, processNstt, getNsttDrilldown, exportNstt } from '../services/nsttApi'
import { NSTT_PIPELINE_STEPS } from '../components/nstt/ProcessingStatus'

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
  const [currentStep, setCurrentStep] = useState(0)
  const [stepStates, setStepStates] = useState({})
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState(null)

  // Navigation and UI state
  const [activeTab, setActiveTab] = useState('summary') // 'summary' | 'failure' | 'raw'
  const [drilldownCategory, setDrilldownCategory] = useState(null)
  const [drilldownData, setDrilldownData] = useState(null)
  const [isDrilldownLoading, setIsDrilldownLoading] = useState(false)
  const [isDrilldownOpen, setIsDrilldownOpen] = useState(false)

  const updateStep = (stepIndex, state = 'complete') => {
    setCurrentStep(stepIndex)
    if (stepIndex >= 0 && stepIndex < NSTT_PIPELINE_STEPS.length) {
      const stepId = NSTT_PIPELINE_STEPS[stepIndex].id
      setStepStates((prev) => ({ ...prev, [stepId]: state }))
    }
  }

  const delay = (ms) => new Promise((res) => setTimeout(res, ms))

  /**
   * Main Pipeline Execution:
   * Coordinates file upload, backend VLOOKUP, Rule Engine classification, and Aggregation
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
    setStepStates({})
    setCurrentStep(0)

    try {
      // Step 1: Namo file loaded
      updateStep(0, 'active')
      await delay(120)
      updateStep(0, 'complete')

      // Step 2: Remedy file loaded
      updateStep(1, 'active')
      await delay(120)
      updateStep(1, 'complete')

      // Step 3: Column validation & VLOOKUP join (Backend Upload)
      updateStep(2, 'active')
      await delay(100)

      const uploadResult = await uploadNsttFiles(file1, file2)
      setUploadId(uploadResult.upload_id)
      setMasterResponse(uploadResult.master_response)
      setStats(uploadResult.stats)
      setWarnings(uploadResult.warnings || [])

      updateStep(2, 'complete') // Columns validated
      updateStep(3, 'complete') // VLOOKUP completed
      updateStep(4, 'complete') // INCIDENT_IMPACT converted
      updateStep(5, 'complete') // Enriched dataset created
      updateStep(6, 'complete') // Duplicate check done
      updateStep(7, 'complete') // Master response JSON ready

      // Step 8 & 9: Rule engine classification & Dashboard aggregation
      updateStep(8, 'active')
      await delay(150)

      const processResult = await processNstt({
        uploadId: uploadResult.upload_id,
        masterResponse: uploadResult.master_response,
      })

      setClassifiedMasterResponse(processResult.classified_master_response)
      setAggregatedResult(processResult.aggregated_result)

      updateStep(8, 'complete') // Rule engine done
      updateStep(9, 'complete') // Aggregation done

      setIsComplete(true)
    } catch (err) {
      const errMsg = err.message || 'An unexpected error occurred during processing.'
      setError(errMsg)
      setStepStates((prev) => ({
        ...prev,
        [NSTT_PIPELINE_STEPS[Math.min(currentStep, NSTT_PIPELINE_STEPS.length - 1)].id]: 'error',
      }))
    } finally {
      setIsProcessing(false)
    }
  }, [namoFile, remedyFile, currentStep])

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
    setCurrentStep(0)
    setStepStates({})
    setIsComplete(false)
    setError(null)
    setActiveTab('summary')
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
        currentStep,
        stepStates,
        isComplete,
        error,
        activeTab,
        setActiveTab,
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
