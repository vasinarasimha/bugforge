import { useId } from 'react'
import Select from 'react-select'

export const getSelectStyles = (hasError) => ({
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
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
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
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    '&:active': {
      backgroundColor: 'var(--primary, #2563eb)',
      color: '#ffffff',
    },
  }),
})

export default function SearchableSelect({
  options = [],
  value,
  onChange,
  placeholder = 'Select an option...',
  isDisabled = false,
  isClearable = true,
  isSearchable = true,
  hasError = false,
  formatOptionLabel,
  className,
  id,
  name,
  ...props
}) {
  const selectId = useId()
  const currentOption = options.find((opt) => 
    opt.value === value || (value !== null && value !== undefined && value !== '' && String(opt.value) === String(value))
  ) || null

  return (
    <Select
      id={id || selectId}
      instanceId={id || selectId}
      name={name}
      className={className}
      options={options}
      value={currentOption}
      onChange={(selected) => onChange?.(selected ? selected.value : null, selected)}
      placeholder={placeholder}
      isDisabled={isDisabled}
      isClearable={isClearable}
      isSearchable={isSearchable}
      styles={getSelectStyles(hasError)}
      menuPortalTarget={typeof document !== 'undefined' ? document.body : null}
      formatOptionLabel={formatOptionLabel}
      {...props}
    />
  )
}
