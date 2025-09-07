import { Link } from 'react-router-dom'
import styles from './EditTaskCard.module.scss'
import { type EditTaskListItem } from '../../../utils/api'

interface EditTaskCardProps {
  task: EditTaskListItem
}

function EditTaskCard({ task }: EditTaskCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      SUCCESS: styles.statusSuccess,
      FAILURE: styles.statusFailure,
      PENDING: styles.statusPending,
      STARTED: styles.statusStarted,
      RETRY: styles.statusRetry,
      REVOKED: styles.statusRevoked,
    }

    const statusLabels = {
      SUCCESS: 'Success',
      FAILURE: 'Failed',
      PENDING: 'Pending',
      STARTED: 'Processing',
      RETRY: 'Retrying',
      REVOKED: 'Cancelled',
    }

    return (
      <span className={`${styles.statusBadge} ${statusClasses[status as keyof typeof statusClasses]}`}>
        {statusLabels[status as keyof typeof statusLabels] || status}
      </span>
    )
  }

  const getEditingModeLabel = (mode: string) => {
    return mode === 'copyedit' ? 'Copyedit' : 'Brevity'
  }

  const getArticleInfo = () => {
    return (
      <div className={styles.articleInfo}>
        <span className={styles.articleTitle}>{task.article_title}</span>
        <span className={styles.separator}>•</span>
        <span className={styles.sectionTitle}>{task.section_title}</span>
      </div>
    )
  }

  return (
    <Link to={`/task/${task.id}`} className={styles.editTaskCard}>
      <div className={styles.cardHeader}>
        <div className={styles.taskInfo}>
          {getArticleInfo()}
          <div className={styles.metadata}>
            <span className={styles.editingMode}>{getEditingModeLabel(task.editing_mode)}</span>
            <span className={styles.separator}>•</span>
            <span className={styles.date}>{formatDate(task.created_at)}</span>
            {task.llm_provider && (
              <>
                <span className={styles.separator}>•</span>
                <span className={styles.provider}>{task.llm_provider.toUpperCase()}</span>
              </>
            )}
          </div>
        </div>
        <div className={styles.statusSection}>
          {getStatusBadge(task.status)}
          {task.changes_count !== undefined && task.changes_count !== null && (
            <span className={styles.changesCount}>
              {task.changes_count} change{task.changes_count !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
      
      {task.completed_at && (
        <div className={styles.cardFooter}>
          <span className={styles.completedAt}>
            Completed: {formatDate(task.completed_at)}
          </span>
        </div>
      )}
    </Link>
  )
}

export default EditTaskCard