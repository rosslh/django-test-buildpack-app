import { Link } from 'react-router-dom'
import Icon from '../../shared/ui/Icon/Icon'
import Document from '~icons/custom/document'
import styles from './TaskHistoryEmptyState.module.scss'

interface TaskHistoryEmptyStateProps {
  hasFilters?: boolean
}

function TaskHistoryEmptyState({ hasFilters = false }: TaskHistoryEmptyStateProps) {
  if (hasFilters) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.content}>
          <div className={styles.icon}>
            <Icon icon={Document} size={32} color="tertiary" />
          </div>
          <h3 className={styles.title}>No tasks match your filters</h3>
          <p className={styles.description}>
            Try adjusting your filters or clearing them to see all tasks.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.emptyState}>
      <div className={styles.content}>
        <div className={styles.icon}>
          <Icon icon={Document} size={32} color="tertiary" />
        </div>
        <h3 className={styles.title}>No edit tasks yet</h3>
        <p className={styles.description}>
          Your edit history will appear here once you create your first task.
        </p>
        <Link to="/" className={styles.primaryAction}>
          Create your first edit
        </Link>
      </div>
    </div>
  )
}

export default TaskHistoryEmptyState