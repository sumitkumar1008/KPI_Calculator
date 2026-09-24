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

function Sidebar({
  isOpen,
  onToggle,
  activeModule = 'kpi',
  onSelectModule = () => {},
}) {
  const [kpiDropdownOpen, setKpiDropdownOpen] = useState(true)

  const handleKpiHeaderClick = () => {
    if (activeModule !== 'kpi') {
      onSelectModule('kpi')
      setKpiDropdownOpen(true)
    } else {
      setKpiDropdownOpen((prev) => !prev)
    }
  }

  const handleKpiChevronClick = (e) => {
    e.stopPropagation()
    setKpiDropdownOpen((prev) => !prev)
  }

  const handleSubItemClick = (id) => {
    if (activeModule !== 'kpi') {
      onSelectModule('kpi')
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    } else {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleNsttClick = () => {
    onSelectModule('nstt')
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
                    onClick={() => handleSubItemClick(item.id)}
                  >
                    <span className="sidebar-item-icon" aria-hidden="true">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 2. NSTT Calculator */}
          <div className={`sidebar-module-group ${activeModule === 'nstt' ? 'is-active-module' : ''}`}>
            <button
              type="button"
              className={`sidebar-item sidebar-item--module ${activeModule === 'nstt' ? 'is-active' : ''}`}
              onClick={handleNsttClick}
            >
              <span className="sidebar-item-icon" aria-hidden="true">⏱</span>
              <span className="sidebar-item-text">NSTT Calculator</span>
            </button>
          </div>
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
