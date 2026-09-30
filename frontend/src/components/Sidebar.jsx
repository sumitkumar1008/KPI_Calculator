import { useState } from 'react'
import './Sidebar.css'

const kpiNavigationItems = [
  { id: 'upload-file', label: 'Upload file', icon: '↑' },
  { id: 'unified-kpi', label: 'Unified KPI', icon: '▦' },
  { id: 'unified-kpi-graph', label: 'Unified KPI graph', icon: '⌁' },
  { id: 'automation-run-counts', label: 'Automation RCA run counts', icon: '▥' },
  { id: 'automation-run-graph', label: 'Automation RCA run Y/N graph', icon: '⌁' },
  { id: 'automation-conclusion-counts', label: 'Automation RCA conclusion counts', icon: '▥' },
  { id: 'automation-conclusion-graph', label: 'Automation RCA conclusion Y/N graph', icon: '⌁' },
  { id: 'raw-data', label: 'Raw data', icon: '▤' },
]

const nsttNavigationItems = [
  { id: 'nstt-heading', label: 'Upload & Process', icon: '↑' },
  { id: 'nstt-summary-matrix', label: 'Summary Matrix', icon: '▦' },
  { id: 'nstt-failure-analysis', label: 'Failure Analysis', icon: '⚠️' },
]


function Sidebar({
  isOpen,
  onToggle,
  activeModule = 'kpi',
  onSelectModule = () => {},
}) {
  const [kpiDropdownOpen, setKpiDropdownOpen] = useState(true)
  const [nsttDropdownOpen, setNsttDropdownOpen] = useState(true)

  const handleKpiHeaderClick = () => {
    if (activeModule !== 'kpi') {
      onSelectModule('kpi')
      setKpiDropdownOpen(true)
    } else {
      setKpiDropdownOpen((prev) => !prev)
    }
  }

  const handleNsttHeaderClick = () => {
    if (activeModule !== 'nstt') {
      onSelectModule('nstt')
      setNsttDropdownOpen(true)
    } else {
      setNsttDropdownOpen((prev) => !prev)
    }
  }

  const handleKpiChevronClick = (e) => {
    e.stopPropagation()
    setKpiDropdownOpen((prev) => !prev)
  }

  const handleNsttChevronClick = (e) => {
    e.stopPropagation()
    setNsttDropdownOpen((prev) => !prev)
  }

  const handleSubItemClick = (id, targetModule = 'kpi') => {
    if (activeModule !== targetModule) {
      onSelectModule(targetModule)
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    } else {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <>
      <button
        type="button"
        className={`sidebar-toggle ${isOpen ? 'is-open' : 'is-closed'}`}
        onClick={onToggle}
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
        title={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        <span aria-hidden="true">{isOpen ? '‹' : '›'}</span>
      </button>

      <aside className={`sidebar ${isOpen ? 'is-open' : 'is-closed'}`} aria-label="Calculator navigation">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark" aria-hidden="true">K</span>
          <span>KPI CALCULATOR</span>
        </div>

        <nav className="sidebar-nav" aria-label="Dashboard modules">
          <p className="sidebar-label">Calculators</p>

          {/* 1. SR Volume Calculator with Dropdown Accordion */}
          <div className={`sidebar-module-group ${activeModule === 'kpi' ? 'is-active-module' : ''}`}>
            <button
              type="button"
              className={`sidebar-item sidebar-item--module ${activeModule === 'kpi' ? 'is-active' : ''}`}
              onClick={handleKpiHeaderClick}
              aria-expanded={kpiDropdownOpen}
            >
              <span className="sidebar-item-icon" aria-hidden="true">📊</span>
              <span className="sidebar-item-text">SR Volume Calculator</span>
              <span
                className={`sidebar-item-chevron ${kpiDropdownOpen ? 'is-open' : ''}`}
                onClick={handleKpiChevronClick}
                aria-label="Toggle SR Volume options"
                title="Toggle options"
              >
                ▼
              </span>
            </button>

            {kpiDropdownOpen && (
              <div className="sidebar-submenu" role="menu">
                {kpiNavigationItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="sidebar-item sidebar-item--sub"
                    onClick={() => handleSubItemClick(item.id, 'kpi')}
                  >
                    <span className="sidebar-item-icon" aria-hidden="true">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 2. NSTT Calculator with Dropdown Accordion */}
          <div className={`sidebar-module-group ${activeModule === 'nstt' ? 'is-active-module' : ''}`}>
            <button
              type="button"
              className={`sidebar-item sidebar-item--module ${activeModule === 'nstt' ? 'is-active' : ''}`}
              onClick={handleNsttHeaderClick}
              aria-expanded={nsttDropdownOpen}
            >
              <span className="sidebar-item-icon" aria-hidden="true">⏱</span>
              <span className="sidebar-item-text">NSTT Calculator</span>
              <span
                className={`sidebar-item-chevron ${nsttDropdownOpen ? 'is-open' : ''}`}
                onClick={handleNsttChevronClick}
                aria-label="Toggle NSTT options"
                title="Toggle options"
              >
                ▼
              </span>
            </button>

            {nsttDropdownOpen && (
              <div className="sidebar-submenu" role="menu">
                {nsttNavigationItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="sidebar-item sidebar-item--sub"
                    onClick={() => handleSubItemClick(item.id, 'nstt')}
                  >
                    <span className="sidebar-item-icon" aria-hidden="true">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
