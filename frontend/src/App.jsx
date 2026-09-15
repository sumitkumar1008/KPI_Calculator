import { useEffect, useState } from 'react'
import FileUpload from './components/FileUpload'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Login from './components/login'
import { GlobalFilterProvider } from './context/GlobalFilterContext'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [theme, setTheme] = useState('light')
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
          theme={theme}
          onToggleTheme={() => setTheme((currentTheme) => currentTheme === 'dark' ? 'light' : 'dark')}
          fileFormat={fileFormat}
          onFileFormatChange={setFileFormat}
        />
        <div className="app-content">
          <Navbar theme={theme} onToggleTheme={() => setTheme((currentTheme) => currentTheme === 'dark' ? 'light' : 'dark')} />

          <section id="upload-file" className="upload-section" aria-labelledby="upload-heading">
            <FileUpload fileFormat={fileFormat} />
          </section>

          <footer className="app-footer"><span className="footer-dot" aria-hidden="true" /> Files stay in your browser during this demo</footer>
        </div>
      </main>
    </GlobalFilterProvider>
  )
}

export default App
