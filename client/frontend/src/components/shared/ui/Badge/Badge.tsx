import React from 'react'
import styles from './Badge.module.scss'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info'
type BadgeSize = 'small' | 'medium'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: BadgeSize
  className?: string
}

function Badge({
  children,
  variant = 'default',
  size = 'medium',
  className = ''
}: BadgeProps) {
  const combinedClassName = [
    styles.badge,
    styles[variant],
    styles[size],
    className
  ].filter(Boolean).join(' ')

  return (
    <span className={combinedClassName}>
      {children}
    </span>
  )
}

export default Badge