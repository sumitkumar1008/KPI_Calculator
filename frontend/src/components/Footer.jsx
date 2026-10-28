import './Footer.css'

export default function Footer() {
  return (
    <footer className="pro-footer" aria-label="Dashboard Footer">
      <div className="pro-footer-glow-bar" aria-hidden="true" />
      <div className="pro-footer-container">
        <p className="pro-footer-title">KPI Calculator Dashboard @ 2026</p>
        <p className="pro-footer-devs">
          <span className="pro-footer-label">Developed by</span>{' '}
          <a href="mailto:aditipand2756@gmail.com" className="pro-footer-link">
            aditipand2756@gmail.com
          </a>
          ,{' '}
          <a href="mailto:rakshitamogha@gmail.com" className="pro-footer-link">
            rakshitamogha@gmail.com
          </a>
          ,{' '}
          <a href="mailto:sumitkr0810@gmail.com" className="pro-footer-link">
            sumitkr0810@gmail.com
          </a>
        </p>
      </div>
    </footer>
  )
}
