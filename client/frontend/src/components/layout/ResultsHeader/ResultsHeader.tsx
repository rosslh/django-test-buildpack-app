import styles from "./ResultsHeader.module.scss";

type EditingMode = "brevity" | "copyedit";

interface ResultsHeaderProps {
  editingMode: EditingMode;
  articleTitle?: string;
  articleUrl?: string;
  sectionTitle?: string;
  changedParagraphs: number;
}

function ResultsHeader({
  editingMode,
  articleTitle,
  articleUrl,
  sectionTitle,
  changedParagraphs,
}: ResultsHeaderProps) {
  return (
    <div className={styles.resultsHeader}>
      <h2 className={styles.resultsTitle}>
        {editingMode === "brevity" ? "Brevity" : "Copyedit"} Results for{" "}
        <a
          href={articleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.resultsLink}
        >
          {articleTitle}
        </a>
        {sectionTitle && (
          <>
            {" - "}
            <span className={styles.sectionTitle}>{sectionTitle}</span>
          </>
        )}
      </h2>
      <p className={styles.resultsDescription}>
        Found {changedParagraphs} paragraph{changedParagraphs !== 1 ? "s" : ""}{" "}
        that can be {editingMode === "brevity" ? "shortened" : "improved"}.
        {changedParagraphs > 0 &&
          " Review the changes below and choose your preferred version for each paragraph."}
      </p>
    </div>
  );
}

export default ResultsHeader;
