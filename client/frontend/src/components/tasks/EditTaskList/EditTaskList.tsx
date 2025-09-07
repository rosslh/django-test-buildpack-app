import { useState, useEffect } from 'react'
import EditTaskCard from '../EditTaskCard/EditTaskCard'
import TaskHistoryEmptyState from '../TaskHistoryEmptyState/TaskHistoryEmptyState'
import styles from './EditTaskList.module.scss'
import { type EditTaskListResponse, type EditTaskListFilters, type EditingMode } from '../../../utils/api'

interface EditTaskListProps {
  taskList: EditTaskListResponse
  filters: EditTaskListFilters
  onFilterChange: (filters: EditTaskListFilters) => void
  onPageChange: (page: number) => void
}

function EditTaskList({ taskList, filters, onFilterChange, onPageChange }: EditTaskListProps) {
  const [statusFilter, setStatusFilter] = useState<string>(filters.status || '')
  const [modeFilter, setModeFilter] = useState<EditingMode | ''>(filters.editing_mode || '')

  // Sync local state with incoming filters
  useEffect(() => {
    setStatusFilter(filters.status || '')
    setModeFilter(filters.editing_mode || '')
  }, [filters.status, filters.editing_mode])

  const handleStatusFilterChange = (status: string) => {
    setStatusFilter(status)
    onFilterChange({ ...filters, status: status || undefined, page: 1 })
  }

  const handleModeFilterChange = (mode: EditingMode | '') => {
    setModeFilter(mode)
    onFilterChange({ ...filters, editing_mode: mode || undefined, page: 1 })
  }

  const handleClearFilters = () => {
    setStatusFilter('')
    setModeFilter('')
    onFilterChange({ 
      page: 1, 
      page_size: filters.page_size,
      status: undefined,
      editing_mode: undefined
    })
  }

  const { results, pagination } = taskList
  const hasActiveFilters = Boolean(statusFilter || modeFilter)

  return (
    <div className={styles.editTaskList}>
      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label htmlFor="status-filter">Status:</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => handleStatusFilterChange(e.target.value)}
            className={styles.filterSelect}
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
            <option value="PENDING">Pending</option>
            <option value="STARTED">Started</option>
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label htmlFor="mode-filter">Mode:</label>
          <select
            id="mode-filter"
            value={modeFilter}
            onChange={(e) => handleModeFilterChange(e.target.value as EditingMode | '')}
            className={styles.filterSelect}
          >
            <option value="">All Modes</option>
            <option value="copyedit">Copyedit</option>
            <option value="brevity">Brevity</option>
          </select>
        </div>

        {(statusFilter || modeFilter) && (
          <button
            onClick={handleClearFilters}
            className={styles.clearFiltersButton}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Show empty state if no results */}
      {results.length === 0 ? (
        <TaskHistoryEmptyState hasFilters={hasActiveFilters} />
      ) : (
        <>
          {/* Results count */}
          <div className={styles.resultsInfo}>
            <span>
              Showing {results.length} of {pagination.total_count} tasks
            </span>
          </div>

          {/* Task cards */}
          <div className={styles.taskCards}>
            {results.map((task) => (
              <EditTaskCard key={task.id} task={task} />
            ))}
          </div>
        </>
      )}

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className={styles.pagination}>
          <button
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={!pagination.has_previous}
            className={styles.paginationButton}
          >
            Previous
          </button>
          
          <span className={styles.paginationInfo}>
            Page {pagination.page} of {pagination.total_pages}
          </span>
          
          <button
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={!pagination.has_next}
            className={styles.paginationButton}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default EditTaskList