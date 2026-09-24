import { useEffect, useState } from 'react'
import FileUpload from './components/FileUpload'
import NsttCalculator from './components/NsttCalculator'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Login from './components/login'
import { GlobalFilterProvider } from './context/GlobalFilterContext'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [theme, setTheme] = useState('light')
  const [activeModule, setActiveModule] = useState('kpi')
  const [fileFormat, setFileFormat] = useState(() => localStorage.getItem('kpi-calculator-file-format') || 'xlsx')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('kpi-calculator-theme-v2', theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem('kpi-calculator-file-format', fileFormat)
  }, [fileFormat])

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />
  }

  return (
    <GlobalFilterProvider>
      <main className={`app-shell theme-${theme} ${sidebarOpen ? '' : 'sidebar-collapsed'}`}>
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen((open) => !open)}
          activeModule={activeModule}
          onSelectModule={setActiveModule}
        />
        <div className="app-content">
          <Navbar
            theme={theme}
            onToggleTheme={() => setTheme((currentTheme) => currentTheme === 'dark' ? 'light' : 'dark')}
            activeModule={activeModule}
          />

          {activeModule === 'kpi' ? (
            <section id="upload-file" className="upload-section" aria-labelledby="upload-heading">
              <FileUpload fileFormat={fileFormat} />
            </section>
          ) : (
            <NsttCalculator fileFormat={fileFormat} />
          )}

          <footer className="app-footer"><span className="footer-dot" aria-hidden="true" /> Files stay in your browser during this demo</footer>
        </div>
      </main>
    </GlobalFilterProvider>
  )
}

export default App
