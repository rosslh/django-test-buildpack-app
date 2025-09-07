import React from 'react'
import Icon from '../Icon/Icon'
import styles from './IconButton.module.scss'

type IconSize = 12 | 16 | 20 | 24 | 32 | 48
type IconColor = 'primary' | 'secondary' | 'tertiary'

interface IconButtonProps {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  onClick?: () => void
  size?: IconSize
  color?: IconColor
  'aria-label'?: string
  title?: string
  disabled?: boolean
  className?: string
}

function IconButton({
  icon,
  onClick,
  size = 16,
  color = 'tertiary',
  'aria-label': ariaLabel,
  title,
  disabled = false,
  className
}: IconButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`${styles.iconButton} ${className || ''}`}
      aria-label={ariaLabel}
      title={title}
      disabled={disabled}
    >
      <Icon icon={icon} size={size} color={color} />
    </button>
  )
}

export default IconButton
