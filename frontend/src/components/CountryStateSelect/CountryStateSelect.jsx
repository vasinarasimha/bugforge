import { useId, useMemo } from 'react'
import Select from 'react-select'
import { getCountries, getStatesByCountry } from '../../data/countriesAndStates'

const customSelectStyles = (hasError) => ({
  control: (provided, state) => ({
    ...provided,
    minHeight: '42px',
    height: '42px',
    borderRadius: 'var(--radius-sm, 8px)',
    borderColor: hasError
      ? 'var(--danger, #ef4444)'
      : state.isFocused
      ? 'var(--primary, #2563eb)'
      : 'var(--border, #d8e4f2)',
    boxShadow: state.isFocused ? '0 0 0 3px rgba(37, 99, 235, 0.15)' : 'none',
    fontSize: '0.9rem',
    backgroundColor: state.isDisabled ? '#f8fafc' : '#ffffff',
    '&:hover': {
      borderColor: hasError ? 'var(--danger, #ef4444)' : 'var(--primary, #2563eb)',
    },
  }),
  valueContainer: (provided) => ({
    ...provided,
    padding: '2px 12px',
  }),
  input: (provided) => ({
    ...provided,
    margin: 0,
    padding: 0,
  }),
  placeholder: (provided) => ({
    ...provided,
    color: '#94a3b8',
    fontSize: '0.9rem',
  }),
  singleValue: (provided) => ({
    ...provided,
    color: 'var(--text-primary, #15203c)',
    fontSize: '0.9rem',
  }),
  menu: (provided) => ({
    ...provided,
    borderRadius: 'var(--radius-sm, 8px)',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
    zIndex: 9999,
    overflow: 'hidden',
    border: '1px solid #e2e8f0',
  }),
  menuPortal: (provided) => ({
    ...provided,
    zIndex: 9999,
  }),
  option: (provided, state) => ({
    ...provided,
    fontSize: '0.88rem',
    backgroundColor: state.isSelected
      ? 'var(--primary, #2563eb)'
      : state.isFocused
      ? '#eff6ff'
      : '#ffffff',
    color: state.isSelected ? '#ffffff' : '#1e293b',
    cursor: 'pointer',
    '&:active': {
      backgroundColor: 'var(--primary, #2563eb)',
      color: '#ffffff',
    },
  }),
})

export default function CountryStateSelect({
  country = '',
  countryCode = '',
  state = '',
  stateCode = '',
  onChangeCountry,
  onChangeState,
  onChange,
  disabled = false,
  errors = {},
  required = false,
}) {
  const countrySelectId = useId()
  const stateSelectId = useId()

  const rawCountries = useMemo(() => getCountries(), [])
  const countryOptions = useMemo(
    () =>
      rawCountries.map((c) => ({
        value: c.name,
        label: `${c.flag} ${c.name}`,
        code: c.code,
      })),
    [rawCountries],
  )

  // Synchronously compute available states for the selected country without any race condition
  const availableStates = useMemo(() => {
    const lookupKey = countryCode || country
    if (!lookupKey) return []
    return getStatesByCountry(lookupKey)
  }, [country, countryCode])

  const stateOptions = useMemo(
    () =>
      availableStates.map((s) => ({
        value: s.name,
        label: s.code ? `${s.name} (${s.code})` : s.name,
        code: s.code,
      })),
    [availableStates],
  )

  // Current selected country formatted for react-select
  const currentCountryValue = useMemo(() => {
    if (!country && !countryCode) return null
    return (
      countryOptions.find(
        (opt) =>
          (country && opt.value.toLowerCase() === country.toLowerCase()) ||
          (countryCode && opt.code.toLowerCase() === countryCode.toLowerCase()),
      ) || (country ? { value: country, label: country, code: countryCode } : null)
    )
  }, [country, countryCode, countryOptions])

  // Current selected state formatted for react-select
  const currentStateValue = useMemo(() => {
    if (!state && !stateCode) return null
    return (
      stateOptions.find(
        (opt) =>
          (state && opt.value.toLowerCase() === state.toLowerCase()) ||
          (stateCode && opt.code.toLowerCase() === stateCode.toLowerCase()),
      ) || (state ? { value: state, label: state, code: stateCode } : null)
    )
  }, [state, stateCode, stateOptions])

  const handleCountryChange = (selectedOption) => {
    const newCountryName = selectedOption ? selectedOption.value : ''
    const newCountryCode = selectedOption ? selectedOption.code : ''

    if (onChange) {
      onChange({
        country: newCountryName,
        country_code: newCountryCode,
        state: '',
        state_code: '',
      })
    } else {
      onChangeCountry && onChangeCountry(newCountryName, newCountryCode)
      onChangeState && onChangeState('', '')
    }
  }

  const handleStateChange = (selectedOption) => {
    const newStateName = selectedOption ? selectedOption.value : ''
    const newStateCode = selectedOption ? selectedOption.code : ''

    if (onChange) {
      onChange({
        country: country,
        country_code: countryCode,
        state: newStateName,
        state_code: newStateCode,
      })
    } else {
      onChangeState && onChangeState(newStateName, newStateCode)
    }
  }

  return (
    <div className="row g-3">
      {/* Searchable Country Select */}
      <div className="col-12 col-md-6">
        <label htmlFor={countrySelectId} className="form-label d-flex justify-content-between mb-1">
          <span className="fw-medium text-dark small">
            Country {required && <span className="text-danger">*</span>}
          </span>
        </label>
        <Select
          inputId={countrySelectId}
          value={currentCountryValue}
          onChange={handleCountryChange}
          options={countryOptions}
          placeholder="🔍 Search & select country..."
          isClearable
          isSearchable
          isDisabled={disabled}
          styles={customSelectStyles(Boolean(errors.country))}
          menuPortalTarget={typeof document !== 'undefined' ? document.body : null}
          menuPosition="fixed"
          noOptionsMessage={() => 'No matching countries found'}
        />
        {errors.country && (
          <div className="text-danger mt-1" style={{ fontSize: '0.8rem' }}>
            {errors.country}
          </div>
        )}
      </div>

      {/* Searchable State / Province Select */}
      <div className="col-12 col-md-6">
        <label htmlFor={stateSelectId} className="form-label d-flex justify-content-between mb-1">
          <span className="fw-medium text-dark small">State / Province</span>
        </label>
        <Select
          inputId={stateSelectId}
          value={currentStateValue}
          onChange={handleStateChange}
          options={stateOptions}
          placeholder={
            !country
              ? 'Select Country first'
              : availableStates.length === 0
              ? 'No states listed (enter city)'
              : '🔍 Search & select state...'
          }
          isClearable
          isSearchable
          isDisabled={disabled || !country}
          styles={customSelectStyles(Boolean(errors.state))}
          menuPortalTarget={typeof document !== 'undefined' ? document.body : null}
          menuPosition="fixed"
          noOptionsMessage={() =>
            !country ? 'Please select a country first' : 'No matching states found'
          }
        />
        {errors.state && (
          <div className="text-danger mt-1" style={{ fontSize: '0.8rem' }}>
            {errors.state}
          </div>
        )}
      </div>
    </div>
  )
}
