// Keep upload rules in one place so the UI and future API integration share them.
export const MAX_FILE_SIZE = 50 * 1024 * 1024
export const ACCEPTED_EXTENSIONS = ['csv', 'xls', 'xlsx']

export function validateFile(file) {
  if (!file) return null

  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !ACCEPTED_EXTENSIONS.includes(extension)) {
    return 'Unsupported file type. Please select a CSV, XLS, or XLSX file.'
  }

  if (file.size > MAX_FILE_SIZE) return 'File size exceeds the 50 MB limit.'

  return null
}

export function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
