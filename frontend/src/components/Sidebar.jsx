import { useState } from 'react'
import './Sidebar.css'

const navigationItems = [
  { id: 'upload-file', label: 'Upload file', icon: '↑' },
  { id: 'unified-kpi', label: 'Unified KPI', icon: '▦' },
  { id: 'unified-kpi-graph', label: 'Unified KPI graph', icon: '⌁' },
  { id: 'automation-run-counts', label: 'Automation RCA run counts', icon: '▥' },
  { id: 'automation-run-graph', label: 'Automation RCA run Y/N graph', icon: '⌁' },
  { id: 'automation-conclusion-counts', label: 'Automation RCA conclusion counts', icon: '▥' },
  { id: 'automation-conclusion-graph', label: 'Automation RCA conclusion Y/N graph', icon: '⌁' },
  { id: 'raw-data', label: 'Raw data', icon: '▤' },
]

const settingsItems = [
  { id: 'profile', label: 'Profile', icon: '◉' },
  { id: 'appearance', label: 'Appearance', icon: '◐' },
  { id: 'file-preferences', label: 'File preferences', icon: '⚙' },
  { id: 'notifications', label: 'Notifications', icon: '♢' },
  { id: 'security', label: 'Security', icon: '◇' },
  { id: 'export-settings', label: 'Export settings', icon: '⇩' },
  { id: 'help-about', label: 'Help & about', icon: '?' },
]

function Sidebar({ isOpen, onToggle, theme, onToggleTheme, fileFormat, onFileFormatChange }) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeSetting, setActiveSetting] = useState(null)
  const [alertsEnabled, setAlertsEnabled] = useState(true)

  const scrollToSection = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const toggleSetting = (id) => {
    setActiveSetting((current) => current === id ? null : id)
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
      <aside className={`sidebar ${isOpen ? 'is-open' : 'is-closed'}`} aria-label="KPI Calculator navigation">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark" aria-hidden="true">K</span>
        <span>KPI CALCULATOR</span>
      </div>

      <nav className="sidebar-nav" aria-label="Dashboard sections">
        <p className="sidebar-label">Workspace</p>
        {navigationItems.map((item) => (
          <button key={item.id} type="button" className="sidebar-item" onClick={() => scrollToSection(item.id)}>
            <span className="sidebar-item-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className={`sidebar-settings ${settingsOpen ? 'is-open' : ''}`}>
        <button
          type="button"
          className="sidebar-settings-toggle"
          aria-expanded={settingsOpen}
          aria-controls="settings-panel"
          onClick={() => setSettingsOpen((open) => !open)}
        >
          <span className="sidebar-item-icon" aria-hidden="true">⚙</span>
          <span>Settings</span>
          <span className="sidebar-chevron" aria-hidden="true">{settingsOpen ? '⌃' : '⌄'}</span>
        </button>

        {settingsOpen && (
          <div id="settings-panel" className="settings-panel" role="dialog" aria-label="Settings">
            <div className="settings-panel-header">
              <div>
                <p className="settings-panel-kicker">Preferences</p>
                <h2>Settings</h2>
              </div>
              <button type="button" className="settings-close" onClick={() => setSettingsOpen(false)} aria-label="Close settings">×</button>
            </div>
            {settingsItems.map((item) => (
              <div key={item.id} className="settings-group">
                <button
                  type="button"
                  className="sidebar-item sidebar-item--quiet"
                  aria-expanded={activeSetting === item.id}
                  onClick={() => toggleSetting(item.id)}
                >
                  <span className="sidebar-item-icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                  <span className="sidebar-chevron" aria-hidden="true">{activeSetting === item.id ? '−' : '+'}</span>
                </button>

                {activeSetting === item.id && (
                  <div className="settings-options">
                    {item.id === 'profile' && <p>Signed-in workspace profile</p>}
                    {item.id === 'appearance' && (
                      <div className="settings-choice-row">
                        <button type="button" className={theme === 'light' ? 'is-selected' : ''} onClick={() => theme !== 'light' && onToggleTheme()}>Light</button>
                        <button type="button" className={theme === 'dark' ? 'is-selected' : ''} onClick={() => theme !== 'dark' && onToggleTheme()}>Dark</button>
                      </div>
                    )}
                    {item.id === 'file-preferences' && (
                      <label className="settings-select-label">Default upload format
                        <select value={fileFormat} onChange={(event) => onFileFormatChange(event.target.value)}>
                          <option value="all">All supported formats</option>
                          <option value="xlsx">Excel (.xlsx)</option>
                          <option value="xls">Excel 97-2003 (.xls)</option>
                          <option value="csv">CSV (.csv)</option>
                        </select>
                      </label>
                    )}
                    {item.id === 'notifications' && (
                      <label className="settings-switch"><input type="checkbox" checked={alertsEnabled} onChange={(event) => setAlertsEnabled(event.target.checked)} /><span>Enable alerts</span></label>
                    )}
                    {item.id === 'security' && (
                      <div className="settings-action-list"><button type="button">Change password</button><button type="button">Session settings</button></div>
                    )}
                    {item.id === 'export-settings' && (
                      <div className="settings-choice-row"><button type="button">CSV</button><button type="button">Excel</button><button type="button">PDF</button></div>
                    )}
                    {item.id === 'help-about' && (
                      <div className="settings-action-list"><button type="button">Help</button><button type="button">Version</button><button type="button">Documentation</button></div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      </aside>
    </>
  )
}

export default Sidebar
