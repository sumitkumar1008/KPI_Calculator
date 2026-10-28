import { useState, useMemo, useEffect, useRef } from 'react'

/**
 * ExcelFilterDropdown
 * An authentic Excel-style column filter dropdown supporting:
 * - Sort A to Z / Sort Z to A
 * - Clear Filter from column
 * - Search within unique values (with Enter-to-apply)
 * - Single-click selection (click item row or "only" button to isolate that single value)
 * - Checkbox toggles for multi-selection
 * - (Select All) with indeterminate state & quick All / Clear links
 * - Scrollable unique values list with record counts & (Blanks) grouping
 * - Apply (OK) / Cancel workflow
 */
export default function ExcelFilterDropdown({
  column,
  alignRight = false,
  availableValues = [],
  currentFilter,
  currentSort,
  onApplyFilter,
  onClearFilter,
  onSort,
  onClose,
}) {
  const dropdownRef = useRef(null)
  const searchInputRef = useRef(null)

  const [searchValue, setSearchValue] = useState('')

  // Initialize draft selection: if column already has an active filter, use it;
  // otherwise default to all available values
  const [draftSelection, setDraftSelection] = useState(() => {
    if (currentFilter instanceof Set) {
      return new Set(currentFilter)
    }
    return new Set(availableValues.map((v) => v.value))
  })

  // Auto-focus the search input on open
  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  // Close on outside click or ESC key (capture phase to avoid bubbling to modal drawer)
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target) &&
        !e.target.closest(`[data-col="${column.id}"]`)
      ) {
        onClose()
      }
    }

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('keydown', handleKeyDown, true)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [column.id, onClose])

  // Filter available values by search query with strict exact-match priority
  const { filteredValues, isExactMatch } = useMemo(() => {
    const term = searchValue.trim()
    if (!term) {
      return { filteredValues: availableValues, isExactMatch: false }
    }

    const termLower = term.toLowerCase()

    // 1. Exact match (case-insensitive) - HIGHEST PRIORITY
    // e.g. "TXN" matches ONLY "TXN" (never "TXN_INFRA"), "IM" matches ONLY "IM" (never "Non-IM")
    const exact = availableValues.filter(
      (item) => item.value.trim().toLowerCase() === termLower
    )
    if (exact.length > 0) {
      return { filteredValues: exact, isExactMatch: true }
    }

    // 2. Starts-with match (case-insensitive) for browsing options while typing
    const startsWithMatches = availableValues.filter((item) =>
      item.value.trim().toLowerCase().startsWith(termLower)
    )
    if (startsWithMatches.length > 0) {
      return { filteredValues: startsWithMatches, isExactMatch: false }
    }

    // 3. Fallback: substring contains (case-insensitive)
    const containsMatches = availableValues.filter((item) =>
      item.value.toLowerCase().includes(termLower)
    )
    return { filteredValues: containsMatches, isExactMatch: false }
  }, [availableValues, searchValue])

  // Sync draft selection whenever search results change so only visible matching items are selected
  useEffect(() => {
    if (searchValue.trim()) {
      setDraftSelection(new Set(filteredValues.map((v) => v.value)))
    }
  }, [searchValue, filteredValues])

  // Select all / indeterminate state for currently visible search results
  const isAllSelected = useMemo(() => {
    if (filteredValues.length === 0) return false
    return filteredValues.every((item) => draftSelection.has(item.value))
  }, [filteredValues, draftSelection])

  const isIndeterminate = useMemo(() => {
    if (filteredValues.length === 0) return false
    const matchCount = filteredValues.filter((item) => draftSelection.has(item.value)).length
    return matchCount > 0 && matchCount < filteredValues.length
  }, [filteredValues, draftSelection])

  // Toggling Select All:
  // If search is active, toggle only matching search results;
  // If search is empty, toggle all available values
  const handleToggleSelectAll = () => {
    setDraftSelection((prev) => {
      const next = new Set(prev)
      if (isAllSelected) {
        // Uncheck all visible items
        filteredValues.forEach((item) => next.delete(item.value))
      } else {
        // Check all visible items
        filteredValues.forEach((item) => next.add(item.value))
      }
      return next
    })
  }

  const handleSelectAll = () => {
    setDraftSelection(new Set(availableValues.map((v) => v.value)))
  }

  const handleClearAllDraft = () => {
    setDraftSelection(new Set())
  }

  // Toggle individual checkbox
  const handleToggleValue = (val) => {
    setDraftSelection((prev) => {
      const next = new Set(prev)
      if (next.has(val)) {
        next.delete(val)
      } else {
        next.add(val)
      }
      return next
    })
  }

  // Single-click selection: select ONLY this value and immediately apply filter!
  const handleSelectOnly = (val) => {
    onApplyFilter(new Set([val]))
    onClose()
  }

  // Enter key in search box: filter immediately by matching search items
  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const matching = filteredValues
        .filter((v) => draftSelection.has(v.value))
        .map((v) => v.value)

      if (matching.length > 0) {
        if (matching.length >= availableValues.length) {
          onClearFilter()
        } else {
          onApplyFilter(new Set(matching))
        }
        onClose()
      } else if (filteredValues.length > 0) {
        if (filteredValues.length >= availableValues.length) {
          onClearFilter()
        } else {
          onApplyFilter(new Set(filteredValues.map((v) => v.value)))
        }
        onClose()
      }
    }
  }

  // Apply button (OK)
  const handleApply = () => {
    // If a search query is active, apply only the checked items within the search results
    if (searchValue.trim() && filteredValues.length > 0) {
      const matchingSelected = filteredValues
        .filter((v) => draftSelection.has(v.value))
        .map((v) => v.value)

      if (matchingSelected.length > 0) {
        onApplyFilter(new Set(matchingSelected))
        onClose()
        return
      }
    }

    // If 0 items selected (user clicked Clear or unchecked all) OR all available values selected:
    // This is equivalent to clearing the filter!
    const isAllAvailableSelected =
      availableValues.length > 0 &&
      availableValues.every((item) => draftSelection.has(item.value))

    if (
      draftSelection.size === 0 ||
      draftSelection.size >= availableValues.length ||
      isAllAvailableSelected
    ) {
      onClearFilter()
    } else {
      onApplyFilter(new Set(draftSelection))
    }
    onClose()
  }

  const isSortedAsc = currentSort?.colId === column.id && currentSort?.direction === 'asc'
  const isSortedDesc = currentSort?.colId === column.id && currentSort?.direction === 'desc'
  const isFiltered = Boolean(currentFilter instanceof Set)

  return (
    <div
      ref={dropdownRef}
      className={`excel-filter-dropdown ${alignRight ? 'align-right' : ''}`}
      onClick={(e) => e.stopPropagation()}
      role="menu"
      aria-label={`Excel filter for ${column.label}`}
    >
      {/* ── Sort & Clear Section ─────────────────────────────── */}
      <div className="dropdown-section-sort">
        <button
          type="button"
          className={`dropdown-btn-item ${isSortedAsc ? 'active' : ''}`}
          onClick={() => {
            onSort('asc')
            onClose()
          }}
        >
          <span className="btn-icon">↑</span> Sort A to Z
        </button>
        <button
          type="button"
          className={`dropdown-btn-item ${isSortedDesc ? 'active' : ''}`}
          onClick={() => {
            onSort('desc')
            onClose()
          }}
        >
          <span className="btn-icon">↓</span> Sort Z to A
        </button>

        {isFiltered && (
          <button
            type="button"
            className="dropdown-btn-item clear-action"
            onClick={() => {
              onClearFilter()
              onClose()
            }}
          >
            <span className="btn-icon">✕</span> Clear Filter from {column.label}
          </button>
        )}
      </div>

      {/* ── Search Input Box ─────────────────────────────────── */}
      <div className="dropdown-section-search">
        <div className="dropdown-search-wrapper">
          <span className="dropdown-search-icon" aria-hidden="true">🔍</span>
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search values (press Enter to apply)..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={handleSearchKeyDown}
          />
          {searchValue && (
            <button
              type="button"
              className="dropdown-search-clear"
              onClick={() => setSearchValue('')}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* ── Select All Row & Quick Actions ───────────────────── */}
      <div className="dropdown-select-all-row">
        <label className="dropdown-checkbox-label select-all-label">
          <input
            type="checkbox"
            checked={isAllSelected}
            ref={(el) => {
              if (el) el.indeterminate = isIndeterminate
            }}
            onChange={handleToggleSelectAll}
          />
          <span>
            {isExactMatch
              ? `(Exact Match: ${filteredValues[0]?.value})`
              : searchValue
                ? '(Select All Search Results)'
                : '(Select All)'}
          </span>
        </label>
        <div className="select-all-actions">
          <button type="button" className="select-all-link" onClick={handleSelectAll}>
            All
          </button>
          <span>•</span>
          <button type="button" className="select-all-link" onClick={handleClearAllDraft}>
            Clear
          </button>
        </div>
      </div>

      {/* ── Scrollable Unique Values List ────────────────────── */}
      <div className="dropdown-values-list">
        {filteredValues.length === 0 ? (
          <div className="dropdown-no-values">No matches found</div>
        ) : (
          filteredValues.map(({ value, count }) => {
            const isChecked = draftSelection.has(value)
            return (
              <div
                key={value}
                className={`dropdown-value-item ${isChecked ? 'is-selected' : ''}`}
                onClick={() => handleSelectOnly(value)}
                title={`Click to show only "${value}"`}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => handleToggleValue(value)}
                  aria-label={`Select ${value}`}
                />
                <span
                  className={`dropdown-val-text ${value === '(Blanks)' ? 'is-blank' : ''}`}
                >
                  {value}
                </span>
                <span className="dropdown-val-count" title={`${count.toLocaleString()} occurrences`}>
                  {count.toLocaleString()}
                </span>
                <button
                  type="button"
                  className="btn-val-only"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleSelectOnly(value)
                  }}
                  title={`Show only ${value}`}
                >
                  Only
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* ── Footer Actions ───────────────────────────────────── */}
      <div className="dropdown-footer">
        {isFiltered && (
          <button
            type="button"
            className="btn-dropdown-clear"
            onClick={() => {
              onClearFilter()
              onClose()
            }}
          >
            Clear Filter
          </button>
        )}
        <button type="button" className="btn-dropdown-cancel" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="btn-dropdown-apply" onClick={handleApply}>
          OK
        </button>
      </div>
    </div>
  )
}
