import Spinner from '../../ui/Spinner/Spinner'
import styles from './LoadingState.module.scss'

interface LoadingStateProps {
  message?: string
}

function LoadingState({ message = "Processing article..." }: LoadingStateProps) {
  return (
    <div className={styles.loadingState}>
      <div className={styles.loadingContent}>
        <Spinner
          size={24}
          color="secondary"
          className={styles.loadingSpinner}
        />
        {message}
      </div>
    </div>
  )
}

export default LoadingState
