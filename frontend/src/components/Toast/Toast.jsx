import { useEffect } from 'react'

export default function Toast({ message, variant = 'success', onClose }) {
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(onClose, 3200)
    return () => clearTimeout(timer)
  }, [message, onClose])

  if (!message) return null

  return (
    <aside className={`toast-notification toast-${variant}`} role="status" aria-live="polite">
      <div className="toast-copy">
        <p>{message}</p>
      </div>
      <button type="button" className="toast-close" onClick={onClose} aria-label="Dismiss notification">
        ×
      </button>
    </aside>
  )
}
