import { createContext, useContext, useMemo, useState } from 'react'

const GlobalFilterContext = createContext({
  globalPeriod: 'monthly',
  setGlobalPeriod: () => {},
  selectedMedia: 'all',
  setSelectedMedia: () => {},
  selectedRoster: 'all',
  setSelectedRoster: () => {},
  availableMediaOptions: [],
  availableRosterOptions: [],
  rawResponse: null,
  setRawResponse: () => {},
  filteredResponse: null,
  filteredRows: [],
  totalRowCount: 0,
  filteredRowCount: 0,
  clearFilters: () => {},
  hasActiveFilters: false,
})

export function GlobalFilterProvider({ children }) {
  const [globalPeriod, setGlobalPeriod] = useState('monthly')
  const [selectedMedia, setSelectedMedia] = useState('all')
  const [selectedRoster, setSelectedRoster] = useState('all')
  const [rawResponse, setRawResponse] = useState(null)

  // Extract distinct, sorted media options from raw rows
  const availableMediaOptions = useMemo(() => {
    if (!rawResponse?.rows || !Array.isArray(rawResponse.rows)) return []
    const set = new Set()
    for (const r of rawResponse.rows) {
      if (r.MEDIA !== null && r.MEDIA !== undefined && String(r.MEDIA).trim() !== '') {
        set.add(String(r.MEDIA).trim())
      }
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
  }, [rawResponse])

  // Extract distinct, sorted roster options from raw rows
  const availableRosterOptions = useMemo(() => {
    if (!rawResponse?.rows || !Array.isArray(rawResponse.rows)) return []
    const set = new Set()
    for (const r of rawResponse.rows) {
      if (r.ROSTER_ALLOCATION !== null && r.ROSTER_ALLOCATION !== undefined && String(r.ROSTER_ALLOCATION).trim() !== '') {
        set.add(String(r.ROSTER_ALLOCATION).trim())
      }
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
  }, [rawResponse])

  // Filter rows by selectedMedia and selectedRoster
  const filteredRows = useMemo(() => {
    if (!rawResponse?.rows || !Array.isArray(rawResponse.rows)) return []

    const hasMedia = selectedMedia && selectedMedia !== 'all'
    const hasRoster = selectedRoster && selectedRoster !== 'all'

    if (!hasMedia && !hasRoster) {
      return rawResponse.rows
    }

    const normMedia = hasMedia ? selectedMedia.toLowerCase() : null
    const normRoster = hasRoster ? selectedRoster.toLowerCase() : null

    return rawResponse.rows.filter((r) => {
      if (normMedia) {
        const rowMedia = r.MEDIA ? String(r.MEDIA).trim().toLowerCase() : ''
        if (rowMedia !== normMedia) return false
      }
      if (normRoster) {
        const rowRoster = r.ROSTER_ALLOCATION ? String(r.ROSTER_ALLOCATION).trim().toLowerCase() : ''
        if (rowRoster !== normRoster) return false
      }
      return true
    })
  }, [rawResponse, selectedMedia, selectedRoster])

  // Memoized response matching the API shape expected by tables/charts
  const filteredResponse = useMemo(() => {
    if (!rawResponse) return null
    return {
      ...rawResponse,
      rows: filteredRows,
      row_count: filteredRows.length,
    }
  }, [rawResponse, filteredRows])

  const totalRowCount = rawResponse?.rows?.length || 0
  const filteredRowCount = filteredRows.length
  const hasActiveFilters = (selectedMedia && selectedMedia !== 'all') || (selectedRoster && selectedRoster !== 'all')

  const clearFilters = () => {
    setSelectedMedia('all')
    setSelectedRoster('all')
  }

  return (
    <GlobalFilterContext.Provider
      value={{
        globalPeriod,
        setGlobalPeriod,
        selectedMedia,
        setSelectedMedia,
        selectedRoster,
        setSelectedRoster,
        availableMediaOptions,
        availableRosterOptions,
        rawResponse,
        setRawResponse,
        filteredResponse,
        filteredRows,
        totalRowCount,
        filteredRowCount,
        clearFilters,
        hasActiveFilters,
      }}
    >
      {children}
    </GlobalFilterContext.Provider>
  )
}

export function useGlobalFilter() {
  const context = useContext(GlobalFilterContext)
  if (!context) {
    throw new Error('useGlobalFilter must be used within a GlobalFilterProvider')
  }
  return context
}

export default GlobalFilterContext
