import styles from './EmptyState.module.scss'
import Document from '~icons/custom/document'
import CheckCircle from '~icons/custom/check-circle'
import Icon from '../../ui/Icon/Icon'

interface EmptyStateProps {
  title?: string
  message?: string
}

function EmptyState({ 
  title = "Ready to Edit Wikipedia Articles",
  message = "Get started by entering a Wikipedia article title in the sidebar. Our AI will analyze the content and suggest improvements to improve its quality and readability."
}: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyStateContent}>
        <div className={styles.emptyStateIcon}>
          <Icon icon={Document} size={48} color="tertiary" />
        </div>
        <h2 className={styles.emptyStateTitle}>{title}</h2>
        <p className={styles.emptyStateDescription}>
          {message}
        </p>
        <div className={styles.emptyStateFeatures}>
          <div className={styles.emptyStateFeature}>
            <div className={styles.emptyStateFeatureIcon}>
              <Icon icon={CheckCircle} size={16} color="primary" />
            </div>
            <span>AI-powered copyediting</span>
          </div>
          <div className={styles.emptyStateFeature}>
            <div className={styles.emptyStateFeatureIcon}>
              <Icon icon={CheckCircle} size={16} color="primary" />
            </div>
            <span>Preserves references and formatting</span>
          </div>
          <div className={styles.emptyStateFeature}>
            <div className={styles.emptyStateFeatureIcon}>
              <Icon icon={CheckCircle} size={16} color="primary" />
            </div>
            <span>Compare before and after versions</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EmptyState
