import { useState, useEffect } from "react";
import EditTaskList from "../EditTaskList/EditTaskList";
import LoadingState from "../../shared/components/LoadingState/LoadingState";
import ErrorMessage from "../../shared/components/ErrorMessage/ErrorMessage";
import styles from "./EditHistoryPage.module.scss";
import {
  fetchEditTaskList,
  type EditTaskListResponse,
  type EditTaskListFilters,
} from "../../../utils/api";

function EditHistoryPage() {
  const [taskList, setTaskList] = useState<EditTaskListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<EditTaskListFilters>({
    page: 1,
    page_size: 20,
  });

  const fetchTasks = async (newFilters?: EditTaskListFilters) => {
    setLoading(true);
    setError(null);

    try {
      const filtersToUse = newFilters || filters;
      const response = await fetchEditTaskList(filtersToUse);
      setTaskList(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch edit history"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilterChange = (newFilters: EditTaskListFilters) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    fetchTasks(updatedFilters);
  };

  const handlePageChange = (page: number) => {
    handleFilterChange({ page });
  };

  return (
    <div className={styles.editHistoryPage}>
      <div className={styles.header}>
        <h1 className={styles.pageTitle}>Edit History</h1>
        <p className={styles.description}>
          View all your edit tasks and their results. Click on any task to view
          detailed changes.
        </p>
      </div>

      <div className={styles.content}>
        {loading && <LoadingState message="Loading edit history..." />}

        {error && <ErrorMessage error={error} />}

        {taskList && !loading && (
          <EditTaskList
            taskList={taskList}
            filters={filters}
            onFilterChange={handleFilterChange}
            onPageChange={handlePageChange}
          />
        )}
      </div>
    </div>
  );
}

export default EditHistoryPage;
