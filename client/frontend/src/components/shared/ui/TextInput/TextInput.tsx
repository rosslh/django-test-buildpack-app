import React from 'react'
import styles from './TextInput.module.scss'

type TextInputSize = 'small' | 'medium' | 'large'

interface TextInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: 'text' | 'email' | 'password' | 'url'
  size?: TextInputSize
  disabled?: boolean
  required?: boolean
  className?: string
  'aria-label'?: string
  'aria-describedby'?: string
  id?: string
  name?: string
}

function TextInput({
  value,
  onChange,
  placeholder,
  type = 'text',
  size = 'medium',
  disabled = false,
  required = false,
  className = '',
  'aria-label': ariaLabel,
  'aria-describedby': ariaDescribedBy,
  id,
  name
}: TextInputProps) {
  const combinedClassName = [
    styles.textInput,
    styles[size],
    disabled && styles.disabled,
    className
  ].filter(Boolean).join(' ')

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.value)
  }

  return (
    <input
      type={type}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      required={required}
      className={combinedClassName}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      id={id}
      name={name}
    />
  )
}

export default TextInput