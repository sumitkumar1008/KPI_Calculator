import { createContext, useContext, useState } from 'react'

const GlobalFilterContext = createContext({
  globalPeriod: 'monthly',
  setGlobalPeriod: () => {},
  filters: { period: 'monthly' },
  updateFilter: () => {},
})

export function GlobalFilterProvider({ children }) {
  const [filters, setFilters] = useState({
    period: 'monthly',
  })

  const setGlobalPeriod = (period) => {
    setFilters((prev) => ({ ...prev, period }))
  }

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <GlobalFilterContext.Provider
      value={{
        globalPeriod: filters.period,
        setGlobalPeriod,
        filters,
        updateFilter,
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
