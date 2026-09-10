import { useEffect, useRef, useState } from 'react'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import './GlobalFilter.css'

function GlobalFilter() {
  const { globalPeriod, setGlobalPeriod } = useGlobalFilter()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const periodLabels = {
    daily: 'Daily',
    weekly: 'Weekly',
    monthly: 'Monthly',
  }

  return (
    <div className="global-filter-wrapper" ref={dropdownRef}>
      <button
        type="button"
        className={`global-filter-btn ${isOpen ? 'is-active' : ''}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        title="Global time period filter"
      >
        <span className="filter-btn-text">Filter</span>
        <span className="filter-active-pill">{periodLabels[globalPeriod] || 'Daily'}</span>
        <svg
          className={`filter-arrow-icon ${isOpen ? 'is-open' : ''}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className="global-filter-dropdown" role="menu" aria-label="Select period filter">
          <div className="dropdown-section-title">Time Period</div>
          {['daily', 'weekly', 'monthly'].map((periodKey) => (
            <button
              key={periodKey}
              type="button"
              className={`dropdown-option ${globalPeriod === periodKey ? 'is-selected' : ''}`}
              onClick={() => {
                setGlobalPeriod(periodKey)
                setIsOpen(false)
              }}
              role="menuitem"
            >
              <span>{periodLabels[periodKey]}</span>
              {globalPeriod === periodKey && <span className="option-check" aria-hidden="true">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default GlobalFilter
