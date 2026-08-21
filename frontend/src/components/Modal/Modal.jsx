import { useEffect } from 'react'
import { createPortal } from 'react-dom'

export default function Modal({ title, children, primaryLabel, secondaryLabel, onPrimary, onSecondary, onClose, bodyStyle, sizeClass = '' }) {
  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  return createPortal(
    <>
      <div className="modal-backdrop fade show" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}></div>
      <div className="modal d-block" role="dialog" aria-modal="true" style={{ zIndex: 1055 }}>
        <div className={`modal-dialog modal-dialog-centered ${sizeClass}`}>
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">{title}</h5>
              <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />
            </div>
            <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto', ...bodyStyle }}>
              {children}
            </div>
            <div className="modal-footer">
              {secondaryLabel && <button type="button" className="btn btn-light" onClick={onSecondary}>{secondaryLabel}</button>}
              {primaryLabel && <button type="button" className="btn btn-primary" onClick={onPrimary}>{primaryLabel}</button>}
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body
  )
}
