import axios from "axios";

// Types for API responses
export interface SectionHeading {
  text: string;
  level: number;
}

export interface SectionHeadingsResponse {
  headings: SectionHeading[];
  article_title: string;
  article_url: string;
}

export interface Paragraph {
  before: string;
  after: string;
  status: "CHANGED" | "UNCHANGED" | "REJECTED" | "SKIPPED" | "ERRORED";
  status_details: string;
}

export interface EditResponse {
  paragraphs: Paragraph[];
  article_title?: string;
  section_title?: string;
  article_url?: string;
}

export interface TaskResponse {
  task_id: string;
  status_url: string;
}

export interface ProgressData {
  total_paragraphs: number;
  progress_percentage: number;
  phase_counts: {
    pending: number;
    pre_processing: number;
    llm_processing: number;
    post_processing: number;
    complete: number;
  };
  paragraphs: Array<{
    index: number;
    phase: "pending" | "pre_processing" | "llm_processing" | "post_processing" | "complete";
    content_preview: string;
    status?: string;
    started_at?: string;
    completed_at?: string;
  }>;
}

export interface TaskStatusResponse {
  task_id: string;
  status: "PENDING" | "SUCCESS" | "FAILURE" | "STARTED" | "RETRY";
  result?: EditResponse;
  error?: string;
  progress?: ProgressData;
}

export type EditingMode = "brevity" | "copyedit";
export type ApiProvider = "google" | "openai" | "anthropic" | "mistral" | "perplexity";

export interface ApiKeyConfig {
  provider: ApiProvider;
  google?: string;
  openai?: string;
  anthropic?: string;
  mistral?: string;
  perplexity?: string;
}

// Utility function to get API headers based on provider
const getApiHeaders = (config: ApiKeyConfig): Record<string, string> => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Use the explicitly selected provider
  if (config.provider === "google" && config.google?.trim()) {
    headers["X-Google-API-Key"] = config.google;
  } else if (config.provider === "openai" && config.openai?.trim()) {
    headers["X-OpenAI-API-Key"] = config.openai;
  } else if (config.provider === "anthropic" && config.anthropic?.trim()) {
    headers["X-Anthropic-API-Key"] = config.anthropic;
  } else if (config.provider === "mistral" && config.mistral?.trim()) {
    headers["X-Mistral-API-Key"] = config.mistral;
  } else if (config.provider === "perplexity" && config.perplexity?.trim()) {
    headers["X-Perplexity-API-Key"] = config.perplexity;
  }

  return headers;
};

// API functions
export const fetchSectionHeadings = async (
  articleTitle: string
): Promise<SectionHeadingsResponse> => {
  const response = await axios.post<SectionHeadingsResponse>(
    "/api/section-headings",
    {
      article_title: articleTitle,
    }
  );
  return response.data;
};

export const editSection = async (
  editingMode: EditingMode,
  articleTitle: string,
  sectionTitle: string,
  apiKeyConfig: ApiKeyConfig
): Promise<TaskResponse> => {
  const response = await axios.post<TaskResponse>(
    `/api/edit/${editingMode}`,
    {
      article_title: articleTitle,
      section_title: sectionTitle,
    },
    {
      headers: getApiHeaders(apiKeyConfig),
    }
  );
  return response.data;
};

export const editContent = async (
  editingMode: EditingMode,
  content: string,
  apiKeyConfig: ApiKeyConfig
): Promise<TaskResponse> => {
  const response = await axios.post<TaskResponse>(
    `/api/edit/${editingMode}`,
    { content },
    {
      headers: getApiHeaders(apiKeyConfig),
    }
  );
  return response.data;
};

export const getTaskStatus = async (
  taskId: string
): Promise<TaskStatusResponse> => {
  const response = await axios.get<TaskStatusResponse>(
    `/api/results/${taskId}`
  );
  return response.data;
};

// Utility function to poll for task results with progress updates
export const pollTaskUntilComplete = async (
  taskId: string,
  onProgress?: (progress: ProgressData) => void,
  pollingInterval = 1000,
  maxAttempts = 200
): Promise<EditResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const response = await getTaskStatus(taskId);

        // Call progress callback if provided and we have progress data
        if (onProgress && response.progress) {
          onProgress(response.progress);
        }

        if (response.status === "SUCCESS" && response.result) {
          resolve(response.result);
          return;
        } else if (response.status === "FAILURE") {
          reject(new Error(response.error || "Task failed"));
          return;
        } else if (attempts >= maxAttempts) {
          reject(new Error("Polling timed out"));
          return;
        }

        attempts++;
        setTimeout(poll, pollingInterval);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
};

// Types for edit history API
export interface EditTaskListItem {
  id: string;
  editing_mode: EditingMode;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED";
  article_title?: string;
  section_title?: string;
  created_at: string;
  completed_at?: string;
  llm_provider?: string;
  llm_model?: string;
  changes_count?: number;
}

export interface EditTaskListResponse {
  results: EditTaskListItem[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface EditTaskDetail {
  id: string;
  editing_mode: EditingMode;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED";
  article_title?: string;
  section_title?: string;
  content?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  llm_provider?: string;
  llm_model?: string;
  result?: EditResponse;
  error_message?: string;
}

export interface EditTaskListFilters {
  page?: number;
  page_size?: number;
  status?: string;
  editing_mode?: EditingMode;
  date_from?: string;
  date_to?: string;
}

// API functions for edit history
export const fetchEditTaskList = async (
  filters?: EditTaskListFilters
): Promise<EditTaskListResponse> => {
  const params = new URLSearchParams();

  if (filters?.page) params.append("page", filters.page.toString());
  if (filters?.page_size)
    params.append("page_size", filters.page_size.toString());
  if (filters?.status) params.append("status", filters.status);
  if (filters?.editing_mode)
    params.append("editing_mode", filters.editing_mode);
  if (filters?.date_from) params.append("date_from", filters.date_from);
  if (filters?.date_to) params.append("date_to", filters.date_to);

  const url = `/api/tasks/${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await axios.get<EditTaskListResponse>(url);
  return response.data;
};

export const fetchEditTaskDetail = async (
  taskId: string
): Promise<EditTaskDetail> => {
  const response = await axios.get<EditTaskDetail>(`/api/tasks/${taskId}/`);
  return response.data;
};
