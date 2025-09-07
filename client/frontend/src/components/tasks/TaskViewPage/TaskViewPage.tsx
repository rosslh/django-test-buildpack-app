import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import EditingInterface from '../../editing/EditingInterface/EditingInterface'
import styles from './TaskViewPage.module.scss'
import { 
  fetchEditTaskDetail, 
  pollTaskUntilComplete, 
  type EditTaskDetail, 
  type ApiKeyConfig,
  type ProgressData
} from '../../../utils/api'

interface TaskViewPageProps {
  onOpenSettings: () => void
  apiKeyConfig: ApiKeyConfig | null
}

function TaskViewPage({ onOpenSettings, apiKeyConfig }: TaskViewPageProps) {
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<EditTaskDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pollingForResults, setPollingForResults] = useState(false)
  const [currentProgress, setCurrentProgress] = useState<ProgressData | null>(null)

  useEffect(() => {
    const fetchTask = async () => {
      if (!taskId) {
        setError('Task ID is required')
        setLoading(false)
        return
      }

      try {
        const taskData = await fetchEditTaskDetail(taskId)
        setTask(taskData)
        
        // If task is still pending or started, poll for results
        if (taskData.status === 'PENDING' || taskData.status === 'STARTED') {
          setPollingForResults(true)
          try {
            const result = await pollTaskUntilComplete(
              taskId,
              (progress) => {
                setCurrentProgress(progress)
              }
            )
            // Update task with the results
            setTask(prev => prev ? { ...prev, status: 'SUCCESS', result } : null)
          } catch {
            // If polling fails, fetch task details again to get the latest status
            try {
              const updatedTask = await fetchEditTaskDetail(taskId)
              setTask(updatedTask)
            } catch (fetchError) {
              setError(fetchError instanceof Error ? fetchError.message : 'Failed to fetch updated task details')
            }
          } finally {
            setPollingForResults(false)
            setCurrentProgress(null)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch task details')
      } finally {
        setLoading(false)
      }
    }

    fetchTask()
  }, [taskId])

  // Determine the state to pass to EditingInterface
  let interfaceData = null
  let interfaceLoading = false
  let interfaceError = null

  if (loading) {
    interfaceLoading = true
  } else if (error) {
    interfaceError = error
  } else if (!task) {
    interfaceError = "Task not found"
  } else if (task.status === 'FAILURE') {
    interfaceError = task.error_message || 'Task failed'
  } else if (task.status === 'PENDING' || task.status === 'STARTED' || pollingForResults) {
    interfaceLoading = true
  } else if (!task.result) {
    interfaceError = "Task has no results to display"
  } else {
    interfaceData = task.result
  }

  // Format the time ago string
  const getTimeAgo = (dateString: string | undefined) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (seconds < 60) return 'just now'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
    const days = Math.floor(hours / 24)
    return `${days} day${days !== 1 ? 's' : ''} ago`
  }

  return (
    <div className={styles.taskViewPage}>
      <div className={styles.contextualHeader}>
        <Link to="/history" className={styles.backLink}>
          ← Back to History
        </Link>
        {task && (
          <>
            <h1 className={styles.title}>
              {task.editing_mode === 'brevity' ? 'Brevity' : 'Copyedit'} Results for {task.article_title}
              {task.section_title && (
                <span className={styles.sectionTitle}> - {task.section_title}</span>
              )}
            </h1>
            {task.created_at && (
              <p className={styles.timeAgo}>{getTimeAgo(task.created_at)}</p>
            )}
          </>
        )}
      </div>
      <div className={styles.interfaceWrapper}>
        <EditingInterface
          initialData={interfaceData}
          initialArticleTitle={task?.article_title}
          initialSectionTitle={task?.section_title}
          isViewingTask={true}
          onOpenSettings={onOpenSettings}
          apiKeyConfig={apiKeyConfig}
          taskUsedProvider={task?.llm_provider}
          taskCreatedAt={task?.created_at}
          initialLoading={interfaceLoading}
          initialError={interfaceError}
          loadingMessage={
            loading ? "Loading task..." : 
            (task?.status === 'PENDING' || task?.status === 'STARTED' || pollingForResults) ? "Processing article..." : 
            undefined
          }
          progressData={currentProgress}
        />
      </div>
    </div>
  )
}

export default TaskViewPage