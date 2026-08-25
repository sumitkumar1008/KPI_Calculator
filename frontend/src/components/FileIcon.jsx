function FileIcon({ compact = false }) {
  return (
    <svg className={compact ? 'file-icon file-icon--compact' : 'file-icon'} viewBox="0 0 48 48" aria-hidden="true">
      <path d="M14 5.5h13l8 8V42.5H14z" />
      <path d="M27 5.5v9h8" />
      <path d="M19 24h11M19 30h11M19 36h7" />
    </svg>
  )
}

export default FileIcon
