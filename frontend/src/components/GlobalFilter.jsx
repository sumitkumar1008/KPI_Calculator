import { useEffect, useRef, useState } from 'react'
import { useGlobalFilter } from '../context/GlobalFilterContext'
import './GlobalFilter.css'

function GlobalFilter() {
  const {
    globalPeriod,
    setGlobalPeriod,
    selectedMedia,
    setSelectedMedia,
    selectedRoster,
    setSelectedRoster,
    availableMediaOptions,
    availableRosterOptions,
    rawResponse,
    filteredRowCount,
    totalRowCount,
    clearFilters,
    hasActiveFilters,
  } = useGlobalFilter()

  const [isOpen, setIsOpen] = useState(false)
  const [openSection, setOpenSection] = useState(null) // 'media' | 'roster' | null
  const [mediaSearch, setMediaSearch] = useState('')
  const [rosterSearch, setRosterSearch] = useState('')
  const containerRef = useRef(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
        setOpenSection(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        if (openSection) {
          setOpenSection(null)
        } else {
          setIsOpen(false)
        }
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, openSection])

  const periodLabels = {
    daily: 'Daily',
    weekly: 'Weekly',
    monthly: 'Monthly',
  }

  const hasData = Boolean(rawResponse?.rows?.length)

  const filteredMediaList = availableMediaOptions.filter((opt) =>
    opt.toLowerCase().includes(mediaSearch.toLowerCase().trim())
  )

  const filteredRosterList = availableRosterOptions.filter((opt) =>
    opt.toLowerCase().includes(rosterSearch.toLowerCase().trim())
  )

  // Calculate active filter count
  const activeSpecificFiltersCount =
    (selectedMedia !== 'all' ? 1 : 0) + (selectedRoster !== 'all' ? 1 : 0)
  const isAnyFilterApplied = activeSpecificFiltersCount > 0 || globalPeriod !== 'monthly'

  const handleResetAll = () => {
    clearFilters()
    setGlobalPeriod('monthly')
    setMediaSearch('')
    setRosterSearch('')
    setOpenSection(null)
  }

  return (
    <div className="global-filter-unified-container" ref={containerRef}>
      {/* Merged Single Trigger Button in Navbar */}
      <button
        type="button"
        className={`unified-filter-trigger-btn ${isOpen ? 'is-active' : ''} ${isAnyFilterApplied ? 'is-filtered' : ''}`}
        onClick={() => {
          setIsOpen((prev) => !prev)
          setOpenSection(null)
        }}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        title="Open Global Filters (Period, Media, Roster)"
      >
        <svg
          className="unified-filter-icon"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        </svg>

        <span className="unified-filter-title">Filters</span>

        <span className="unified-filter-summary-pill">
          {periodLabels[globalPeriod] || 'Monthly'}
        </span>

        {activeSpecificFiltersCount > 0 && (
          <span
            className="unified-filter-badge"
            title={`${activeSpecificFiltersCount} active filter${activeSpecificFiltersCount > 1 ? 's' : ''}`}
          >
            +{activeSpecificFiltersCount}
          </span>
        )}

        <svg
          className={`unified-filter-arrow ${isOpen ? 'is-open' : ''}`}
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

      {/* Merged Single Dropdown Menu Containing All 3 Filters */}
      {isOpen && (
        <div className="unified-filter-dropdown" role="dialog" aria-label="Global Filters">
          {/* Header */}
          <div className="dropdown-panel-header">
            <div className="dropdown-panel-title-area">
              <span className="dropdown-panel-title">Filter Options</span>
              {hasData && (
                <span className="dropdown-panel-count-badge">
                  {filteredRowCount.toLocaleString()} / {totalRowCount.toLocaleString()} rows
                </span>
              )}
            </div>

            {isAnyFilterApplied && (
              <button
                type="button"
                className="dropdown-panel-reset-btn"
                onClick={handleResetAll}
                title="Reset all filters to defaults"
              >
                Reset all
              </button>
            )}
          </div>

          <div className="dropdown-panel-content">
            {/* 1. Time Period Filter */}
            <div className="filter-group">
              <div className="filter-group-header">
                <span className="filter-group-label">Time Period</span>
                <span className="filter-group-subvalue">{periodLabels[globalPeriod]}</span>
              </div>
              <div className="period-segmented-control" role="group" aria-label="Time period selection">
                {['daily', 'weekly', 'monthly'].map((pKey) => (
                  <button
                    key={pKey}
                    type="button"
                    className={`period-segment-btn ${globalPeriod === pKey ? 'is-selected' : ''}`}
                    onClick={() => setGlobalPeriod(pKey)}
                  >
                    {periodLabels[pKey]}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-section-divider" />

            {/* 2. Media Subtype Filter */}
            <div className="filter-group">
              <div className="filter-group-header">
                <span className="filter-group-label">Media Subtype</span>
                {selectedMedia !== 'all' && (
                  <button
                    type="button"
                    className="filter-clear-link"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedMedia('all')
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="filter-sub-select-wrap">
                <button
                  type="button"
                  className={`filter-sub-select-trigger ${openSection === 'media' ? 'is-open' : ''} ${selectedMedia !== 'all' ? 'is-filtered' : ''}`}
                  onClick={() => setOpenSection((prev) => (prev === 'media' ? null : 'media'))}
                  disabled={!hasData}
                  aria-expanded={openSection === 'media'}
                >
                  <span className="truncate-text">
                    {selectedMedia === 'all' ? 'All Media' : selectedMedia}
                  </span>
                  <svg
                    className={`filter-arrow-icon ${openSection === 'media' ? 'is-open' : ''}`}
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

                {!hasData && (
                  <p className="filter-empty-hint">Upload a file to enable media filtering</p>
                )}

                {openSection === 'media' && hasData && (
                  <div className="filter-sub-dropdown-panel">
                    {availableMediaOptions.length > 5 && (
                      <div className="dropdown-search-wrap">
                        <input
                          type="text"
                          className="dropdown-search-input"
                          placeholder="Search media..."
                          value={mediaSearch}
                          onChange={(e) => setMediaSearch(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          autoFocus
                        />
                      </div>
                    )}

                    <div className="dropdown-scroll-list">
                      <button
                        type="button"
                        className={`dropdown-option ${selectedMedia === 'all' ? 'is-selected' : ''}`}
                        onClick={() => {
                          setSelectedMedia('all')
                          setOpenSection(null)
                          setMediaSearch('')
                        }}
                      >
                        <span>All Media</span>
                        {selectedMedia === 'all' && <span className="option-check" aria-hidden="true">✓</span>}
                      </button>

                      {filteredMediaList.map((media) => (
                        <button
                          key={media}
                          type="button"
                          className={`dropdown-option ${selectedMedia === media ? 'is-selected' : ''}`}
                          onClick={() => {
                            setSelectedMedia(media)
                            setOpenSection(null)
                            setMediaSearch('')
                          }}
                        >
                          <span className="truncate-text">{media}</span>
                          {selectedMedia === media && <span className="option-check" aria-hidden="true">✓</span>}
                        </button>
                      ))}

                      {filteredMediaList.length === 0 && (
                        <div className="dropdown-empty-state">No matching media found</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="filter-section-divider" />

            {/* 3. Roster Allocation Filter */}
            <div className="filter-group">
              <div className="filter-group-header">
                <span className="filter-group-label">Roster Allocation</span>
                {selectedRoster !== 'all' && (
                  <button
                    type="button"
                    className="filter-clear-link"
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedRoster('all')
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="filter-sub-select-wrap">
                <button
                  type="button"
                  className={`filter-sub-select-trigger ${openSection === 'roster' ? 'is-open' : ''} ${selectedRoster !== 'all' ? 'is-filtered' : ''}`}
                  onClick={() => setOpenSection((prev) => (prev === 'roster' ? null : 'roster'))}
                  disabled={!hasData}
                  aria-expanded={openSection === 'roster'}
                >
                  <span className="truncate-text">
                    {selectedRoster === 'all' ? 'All Rosters' : selectedRoster}
                  </span>
                  <svg
                    className={`filter-arrow-icon ${openSection === 'roster' ? 'is-open' : ''}`}
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

                {!hasData && (
                  <p className="filter-empty-hint">Upload a file to enable roster filtering</p>
                )}

                {openSection === 'roster' && hasData && (
                  <div className="filter-sub-dropdown-panel">
                    {availableRosterOptions.length > 5 && (
                      <div className="dropdown-search-wrap">
                        <input
                          type="text"
                          className="dropdown-search-input"
                          placeholder="Search roster..."
                          value={rosterSearch}
                          onChange={(e) => setRosterSearch(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          autoFocus
                        />
                      </div>
                    )}

                    <div className="dropdown-scroll-list">
                      <button
                        type="button"
                        className={`dropdown-option ${selectedRoster === 'all' ? 'is-selected' : ''}`}
                        onClick={() => {
                          setSelectedRoster('all')
                          setOpenSection(null)
                          setRosterSearch('')
                        }}
                      >
                        <span>All Rosters</span>
                        {selectedRoster === 'all' && <span className="option-check" aria-hidden="true">✓</span>}
                      </button>

                      {filteredRosterList.map((roster) => (
                        <button
                          key={roster}
                          type="button"
                          className={`dropdown-option ${selectedRoster === roster ? 'is-selected' : ''}`}
                          onClick={() => {
                            setSelectedRoster(roster)
                            setOpenSection(null)
                            setRosterSearch('')
                          }}
                        >
                          <span className="truncate-text">{roster}</span>
                          {selectedRoster === roster && <span className="option-check" aria-hidden="true">✓</span>}
                        </button>
                      ))}

                      {filteredRosterList.length === 0 && (
                        <div className="dropdown-empty-state">No matching rosters found</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="dropdown-panel-footer">
            <div className="dropdown-footer-summary">
              <span className={`summary-dot ${hasActiveFilters ? 'is-active' : ''}`} aria-hidden="true" />
              <span>
                {hasActiveFilters ? `${activeSpecificFiltersCount} active filter${activeSpecificFiltersCount > 1 ? 's' : ''}` : 'Default filters'}
              </span>
            </div>
            <button
              type="button"
              className="dropdown-done-btn"
              onClick={() => {
                setIsOpen(false)
                setOpenSection(null)
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default GlobalFilter
