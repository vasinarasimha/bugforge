export default function Modal({ title, children, primaryLabel, secondaryLabel, onPrimary, onSecondary, onClose }) {
  return (
    <div className="modal d-block" role="dialog" aria-modal="true">
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">{title}</h5>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close" />
          </div>
          <div className="modal-body">
            {children}
          </div>
          <div className="modal-footer">
            {secondaryLabel && <button type="button" className="btn btn-light" onClick={onSecondary}>{secondaryLabel}</button>}
            {primaryLabel && <button type="button" className="btn btn-primary" onClick={onPrimary}>{primaryLabel}</button>}
          </div>
        </div>
      </div>
    </div>
  )
}
