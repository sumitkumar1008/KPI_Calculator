import { useEffect, useRef, useState } from 'react'
import './DownloadDropdown.css'

function DownloadDropdown({
  onDownloadExcel,
  onDownloadCsv,
  onDownloadImage,
  buttonLabel = 'Download',
  disabled = false,
  tooltip = 'Download table or chart',
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [activeAction, setActiveAction] = useState(null)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick)
      document.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const handleAction = async (actionFn, actionName) => {
    if (!actionFn || isLoading) return
    setIsLoading(true)
    setActiveAction(actionName)
    try {
      await actionFn()
    } catch (err) {
      console.error(`Export ${actionName} error:`, err)
      alert(err.message || `Failed to export as ${actionName}`)
    } finally {
      setIsLoading(false)
      setActiveAction(null)
      setIsOpen(false)
    }
  }

  return (
    <div className="download-dropdown" ref={dropdownRef}>
      <button
        type="button"
        className={`download-dropdown__trigger ${isOpen ? 'is-active' : ''}`}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        disabled={disabled || isLoading}
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={tooltip}
      >
        {isLoading ? (
          <span className="download-dropdown__spinner" aria-hidden="true" />
        ) : (
          <svg className="download-dropdown__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        )}
        <span className="download-dropdown__label">
          {isLoading ? (activeAction ? `Exporting ${activeAction}...` : 'Exporting...') : buttonLabel}
        </span>
        <svg className={`download-dropdown__chevron ${isOpen ? 'is-rotated' : ''}`} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>

      {isOpen && (
        <div className="download-dropdown__menu" role="menu">
          <div className="download-dropdown__header">Export formats</div>

          {onDownloadExcel && (
            <button
              type="button"
              className="download-dropdown__item"
              role="menuitem"
              onClick={() => handleAction(onDownloadExcel, 'Excel')}
              disabled={isLoading}
            >
              <span className="download-dropdown__badge badge--excel" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                  <path d="M8.5 17l2.2-3.3L8.5 10.5h1.7l1.3 2.1 1.3-2.1h1.7l-2.2 3.2 2.3 3.3h-1.8l-1.3-2.2-1.4 2.2H8.5z" />
                </svg>
              </span>
              <div className="download-dropdown__item-info">
                <span className="download-dropdown__item-title">Excel Workbook</span>
                <span className="download-dropdown__item-desc">Formatted .xlsx spreadsheet</span>
              </div>
            </button>
          )}

          {onDownloadCsv && (
            <button
              type="button"
              className="download-dropdown__item"
              role="menuitem"
              onClick={() => handleAction(onDownloadCsv, 'CSV')}
              disabled={isLoading}
            >
              <span className="download-dropdown__badge badge--csv" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="8" y1="13" x2="16" y2="13" />
                  <line x1="8" y1="17" x2="16" y2="17" />
                </svg>
              </span>
              <div className="download-dropdown__item-info">
                <span className="download-dropdown__item-title">CSV File</span>
                <span className="download-dropdown__item-desc">Comma-separated values (.csv)</span>
              </div>
            </button>
          )}

          {onDownloadImage && (
            <button
              type="button"
              className="download-dropdown__item"
              role="menuitem"
              onClick={() => handleAction(onDownloadImage, 'Image')}
              disabled={isLoading}
            >
              <span className="download-dropdown__badge badge--image" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </span>
              <div className="download-dropdown__item-info">
                <span className="download-dropdown__item-title">Chart Image</span>
                <span className="download-dropdown__item-desc">High-resolution PNG (.png)</span>
              </div>
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default DownloadDropdown
