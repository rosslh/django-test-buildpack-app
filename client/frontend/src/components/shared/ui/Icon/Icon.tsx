import React from 'react'
import styles from './Icon.module.scss'

type IconSize = 12 | 16 | 20 | 24 | 32 | 48
type IconColor = 'primary' | 'secondary' | 'tertiary'

interface IconProps {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  size: IconSize
  color: IconColor
  className?: string
}

function Icon({ icon: IconComponent, size, color, className }: IconProps) {
  const combinedClassName = [
    styles.icon,
    styles[`size${size}`],
    styles[color],
    className
  ].filter(Boolean).join(' ')

  return (
    <IconComponent
      className={combinedClassName}
      width={size}
      height={size}
    />
  )
}

export default Icon
