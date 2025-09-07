import styles from './Spinner.module.scss'

interface SpinnerProps {
  size?: number
  color?: 'primary' | 'secondary' | 'on-primary' | 'muted'
  className?: string
}

function Spinner({
  size = 24,
  color = 'secondary',
  className = ''
}: SpinnerProps) {
  return (
    <svg
      className={`${styles.spinner} ${styles[`color-${color}`]} ${className}`}
      style={{ width: size, height: size }}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className={styles.opacity25}
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className={styles.opacity75}
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

export default Spinner
