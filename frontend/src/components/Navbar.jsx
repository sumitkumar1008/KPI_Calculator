import './Navbar.css'

const airtelLogo = 'https://res.cloudinary.com/i4j3dcjs/image/upload/v1787204293/airtel_logo-removebg-preview.png'

function Navbar({ theme, onToggleTheme }) {
  return (
    <header className="app-header">
      <div>
        <p className="eyebrow">Data workspace</p>
        <h1>KPI Calculator</h1>
        <p className="subtitle">Upload your data file to get started</p>
      </div>
      <div className="header-actions">
        <button
          className="theme-toggle"
          type="button"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          <span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span>
        </button>
        <img className="brand-logo" src={airtelLogo} alt="Airtel" />
      </div>
    </header>
  )
}

export default Navbar
