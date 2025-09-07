import styles from './ErrorMessage.module.scss'
import ErrorCircle from '~icons/custom/error-circle'
import Icon from '../../ui/Icon/Icon'

interface ErrorMessageProps {
  error: string
}

function ErrorMessage({ error }: ErrorMessageProps) {
  return (
    <div className={styles.error}>
      <div className={styles.errorContent}>
        <div className={styles.errorIcon}>
          <Icon icon={ErrorCircle} size={20} color="secondary" />
        </div>
        <div className={styles.errorText}>
          <h3 className={styles.errorTitle}>Error</h3>
          <div className={styles.errorMessage}>{error}</div>
        </div>
      </div>
    </div>
  )
}

export default ErrorMessage
