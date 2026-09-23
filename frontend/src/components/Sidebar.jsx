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

function Sidebar({ isOpen, onToggle }) {
  const scrollToSection = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
      </aside>
    </>
  )
}

export default Sidebar
