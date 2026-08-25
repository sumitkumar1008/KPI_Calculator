import { useEffect, useState } from 'react'
import FileUpload from './components/FileUpload'
import Navbar from './components/Navbar'
import './App.css'

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('kpi-calculator-theme') || 'dark')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('kpi-calculator-theme', theme)
  }, [theme])

  return (
    <main className={`app-shell theme-${theme}`}>
      <Navbar theme={theme} onToggleTheme={() => setTheme((currentTheme) => currentTheme === 'dark' ? 'light' : 'dark')} />

      <section className="upload-section" aria-labelledby="upload-heading">
        <FileUpload />
      </section>

      <footer className="app-footer"><span className="footer-dot" aria-hidden="true" /> Files stay in your browser during this demo</footer>
    </main>
  )
}

export default App
