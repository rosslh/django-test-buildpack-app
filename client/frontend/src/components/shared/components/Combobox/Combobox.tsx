import { Combobox as HeadlessCombobox, ComboboxInput, ComboboxButton, ComboboxOption, ComboboxOptions } from '@headlessui/react'
import { useRef } from 'react'
import ChevronDown from '~icons/custom/chevron-down'
import Close from '~icons/custom/close'
import Icon from '../../ui/Icon/Icon'
import Spinner from '../../ui/Spinner/Spinner'
import styles from './Combobox.module.scss'

interface ComboboxOption {
  value: string
  label: string
}

interface ComboboxProps {
  id?: string
  value: string | null
  onChange: (value: string) => void
  options: ComboboxOption[]
  loading?: boolean
  disabled?: boolean
  emptyStateText?: string
  loadingStateText?: string
  className?: string
  hasPrerequisite?: boolean // e.g., whether article title is entered
}

function Combobox({
  id,
  value,
  onChange,
  options,
  loading = false,
  disabled = false,
  emptyStateText = 'No options found',
  loadingStateText = 'Loading...',
  className = '',
  hasPrerequisite = true,
}: ComboboxProps) {
  const filteredOptions = !value || value.trim() === ''
    ? options
    : options.filter((option) =>
        option.label.toLowerCase().includes(value.toLowerCase())
      )

  const isDisabled = disabled || loading || !hasPrerequisite
  const hasValue = value && value.trim().length > 0
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClear = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onChange('')
  }

  const handleWrapperClick = (e: React.MouseEvent) => {
    // Only focus input if clicked outside of buttons
    const target = e.target as HTMLElement
    if (!target.closest(`.${styles.buttonGroup}`) && inputRef.current) {
      inputRef.current.focus()
    }
  }

  return (
    <div className={styles.comboboxWrapper} onClick={handleWrapperClick}>
      <HeadlessCombobox
        immediate
        value={value || ''}
        onChange={onChange}
      >
        <div className={styles.comboboxContainer}>
          <ComboboxInput
            ref={inputRef}
            id={id}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Select section"
            className={`${styles.input} ${className}`}
            disabled={isDisabled}
          />
          <div className={styles.buttonGroup}>
            {hasValue && !isDisabled && (
              <button
                type="button"
                onClick={handleClear}
                className={styles.clearButton}
                aria-label="Clear selection"
              >
                <Icon
                  icon={Close}
                  size={16}
                  color="tertiary"
                />
              </button>
            )}
            <ComboboxButton className={styles.comboboxButton} disabled={isDisabled}>
              {loading ? (
                <Spinner size={16} color="muted" />
              ) : (
                <Icon
                  icon={ChevronDown}
                  size={16}
                  color="tertiary"
                  className={styles.chevronIcon}
                />
              )}
            </ComboboxButton>
          </div>
          <ComboboxOptions
            anchor="bottom start"
            className={styles.comboboxOptions}
          >
            {filteredOptions.map((option) => (
              <ComboboxOption
                key={option.value}
                value={option.value}
                className={styles.comboboxOption}
              >
                {option.label}
              </ComboboxOption>
            ))}
            {filteredOptions.length === 0 && !loading && value?.trim() && (
              <div className={styles.comboboxEmptyState}>
                {emptyStateText}
              </div>
            )}
            {loading && (
              <div className={styles.comboboxLoadingState}>
                <Spinner size={16} color="muted" />
                {loadingStateText}
              </div>
            )}
          </ComboboxOptions>
        </div>
      </HeadlessCombobox>
    </div>
  )
}

export default Combobox
export type { ComboboxOption, ComboboxProps }
