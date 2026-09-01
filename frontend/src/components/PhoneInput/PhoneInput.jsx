import { getDialCodes } from '../../data/countriesAndStates'

export default function PhoneInput({
  countryCode = '+91',
  phoneNumber = '',
  onChangeCountryCode,
  onChangePhoneNumber,
  disabled = false,
  error = '',
  required = false,
}) {
  const dialCodes = getDialCodes()

  return (
    <div className="phone-input-group">
      <div className="d-flex gap-2">
        <div style={{ minWidth: '130px', flex: '0 0 auto' }}>
          <select
            className="form-select"
            value={countryCode || '+91'}
            onChange={(e) => onChangeCountryCode && onChangeCountryCode(e.target.value)}
            disabled={disabled}
            style={{
              borderRadius: 'var(--radius-sm, 8px)',
              borderColor: error ? 'var(--danger, #ef4444)' : 'var(--border, #d8e4f2)',
              fontSize: '0.9rem',
              height: '42px',
            }}
          >
            {dialCodes.map((c) => (
              <option key={`${c.code}-${c.dialCode}`} value={c.dialCode}>
                {c.flag} {c.dialCode} ({c.code})
              </option>
            ))}
          </select>
        </div>
        <div className="flex-grow-1">
          <input
            type="tel"
            className={`form-control ${error ? 'is-invalid' : ''}`}
            placeholder="e.g. 9876543210"
            value={phoneNumber || ''}
            autoComplete="off"
            onChange={(e) => {
              // Allow digits, spaces, hyphens
              const val = e.target.value.replace(/[^0-9\s\-]/g, '')
              onChangePhoneNumber && onChangePhoneNumber(val)
            }}
            disabled={disabled}
            required={required}
            style={{
              borderRadius: 'var(--radius-sm, 8px)',
              borderColor: error ? 'var(--danger, #ef4444)' : 'var(--border, #d8e4f2)',
              fontSize: '0.9rem',
              height: '42px',
            }}
          />
        </div>
      </div>
      {error && (
        <small className="text-danger d-block mt-1" style={{ fontSize: '0.8rem' }}>
          {error}
        </small>
      )}
    </div>
  )
}
