import EmptyState from "../../shared/components/EmptyState/EmptyState";
import ErrorMessage from "../../shared/components/ErrorMessage/ErrorMessage";
import LoadingState from "../../shared/components/LoadingState/LoadingState";
import ProgressDisplay from "../../shared/components/ProgressDisplay/ProgressDisplay";
import DiffList from "../../shared/components/DiffList/DiffList";
import styles from "./MainContent.module.scss";
import type { EditResponse, ProgressData } from "../../../utils/api";

// Types
interface Paragraph {
  before: string;
  after: string;
  status: "CHANGED" | "UNCHANGED" | "REJECTED" | "SKIPPED" | "ERRORED";
  status_details: string;
}

type Selection = "before" | "after";
type EditingMode = "brevity" | "copyedit";

type RenderItem =
  | { type: "CHANGED"; paragraph: Paragraph; originalIndex: number }
  | { type: "UNCHANGED_GROUP"; paragraphs: Paragraph[]; originalIndex: number };

interface MainContentProps {
  data: EditResponse | null;
  loading: boolean;
  error: string | null;
  editingMode: EditingMode;
  selections: Record<number, Selection>;
  copied: boolean;
  changedParagraphs: number;
  allSelectionsMade: boolean;
  renderItems: RenderItem[];
  onSelectionChange: (index: number, selection: Selection) => void;
  onCopyToClipboard: () => void;
  loadingMessage?: string;
  progressData?: ProgressData | null;
  isViewingTask?: boolean;
}

function MainContent({
  data,
  loading,
  error,
  editingMode,
  selections,
  copied,
  changedParagraphs,
  allSelectionsMade,
  renderItems,
  onSelectionChange,
  onCopyToClipboard,
  loadingMessage,
  progressData,
  isViewingTask = false,
}: MainContentProps) {
  return (
    <main className={styles.main}>
      {!data && !loading && !error && <EmptyState />}
      {error && <ErrorMessage error={error} />}
      {loading && !progressData && <LoadingState message={loadingMessage} />}
      {loading && progressData && <ProgressDisplay progress={progressData} message={loadingMessage} />}

      {/* Results */}
      {data && (
        <div className={styles.results}>
          <DiffList
            renderItems={renderItems}
            selections={selections}
            onSelectionChange={onSelectionChange}
            editingMode={editingMode}
            articleTitle={data.article_title}
            articleUrl={data.article_url}
            sectionTitle={data.section_title}
            changedParagraphs={changedParagraphs}
            allSelectionsMade={allSelectionsMade}
            copied={copied}
            onCopyToClipboard={onCopyToClipboard}
            hideHeader={isViewingTask}
          />
        </div>
      )}
    </main>
  );
}

export default MainContent;
