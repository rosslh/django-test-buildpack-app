import CheckCircleIcon from "~icons/custom/check-circle";
import Icon from "../../shared/ui/Icon/Icon";
import styles from "./SidebarHeader.module.scss";
import { type ApiKeyConfig } from "../../../utils/api";

interface SidebarHeaderProps {
  apiKeyConfig: ApiKeyConfig | null;
  taskUsedProvider?: string;
  taskCreatedAt?: string;
  isViewingTask?: boolean;
  onOpenSettings: () => void;
}

function SidebarHeader({
  apiKeyConfig,
  taskUsedProvider,
  taskCreatedAt,
  isViewingTask = false,
  onOpenSettings,
}: SidebarHeaderProps) {
  const getProviderDisplayName = (provider: string) => {
    switch (provider) {
      case "google":
        return "Google (Gemini)";
      case "openai":
        return "OpenAI (GPT)";
      case "anthropic":
        return "Anthropic (Claude)";
      case "mistral":
        return "Mistral";
      case "perplexity":
        return "Perplexity";
      default:
        return provider;
    }
  };

  const formatCreatedDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const displayProvider =
    isViewingTask && taskUsedProvider
      ? taskUsedProvider
      : apiKeyConfig?.provider;
  const showApiKeyRequired = !apiKeyConfig && !isViewingTask;

  return (
    <div className={styles.sidebarHeader}>
      {!isViewingTask && (
        <p className={styles.subtitle}>Copyedit Wikipedia articles using AI</p>
      )}

      {isViewingTask && taskCreatedAt && (
        <div className={styles.taskInfo}>
          <label className={styles.modelLabel}>Created</label>
          <span className={styles.createdDate}>
            {formatCreatedDate(taskCreatedAt)}
          </span>
        </div>
      )}

      {displayProvider && (
        <div className={styles.modelSection}>
          <label className={styles.modelLabel}>AI Model</label>
          <button onClick={onOpenSettings} className={styles.apiStatus}>
            <span className={styles.apiProvider}>
              {getProviderDisplayName(displayProvider)}
            </span>
            <Icon icon={CheckCircleIcon} size={12} color="secondary" />
          </button>
        </div>
      )}

      {showApiKeyRequired && (
        <button onClick={onOpenSettings} className={styles.apiWarning}>
          API Key Required
        </button>
      )}
    </div>
  );
}

export default SidebarHeader;
