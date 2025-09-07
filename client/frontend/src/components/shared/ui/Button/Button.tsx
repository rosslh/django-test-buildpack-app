import React from 'react'
import { Link } from 'react-router-dom'
import styles from './Button.module.scss'

type ButtonVariant = 'primary' | 'secondary' | 'accent'
type ButtonSize = 'small' | 'medium' | 'large'

interface BaseButtonProps {
  children: React.ReactNode
  variant?: ButtonVariant
  size?: ButtonSize
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

interface LinkButtonProps extends BaseButtonProps {
  href: string
  onClick?: never
  type?: never
}

interface ActionButtonProps extends BaseButtonProps {
  href?: never
  onClick?: () => void
  type?: 'button' | 'submit' | 'reset'
}

type ButtonProps = LinkButtonProps | ActionButtonProps

function Button(props: ButtonProps) {
  const {
    children,
    variant = 'primary',
    size = 'medium',
    disabled = false,
    className = '',
    'aria-label': ariaLabel
  } = props

  const combinedClassName = [
    styles.button,
    styles[variant],
    styles[size],
    disabled && styles.disabled,
    className
  ].filter(Boolean).join(' ')

  if ('href' in props && props.href) {
    return (
      <Link
        to={props.href}
        className={combinedClassName}
        aria-label={ariaLabel}
      >
        {children}
      </Link>
    )
  }

  return (
    <button
      type={props.type || 'button'}
      onClick={props.onClick}
      className={combinedClassName}
      disabled={disabled}
      aria-label={ariaLabel}
    >
      {children}
    </button>
  )
}

export default Button