import { forwardRef, useMemo } from "react";
import { Virtuoso } from "react-virtuoso";
import DiffViewer from "../DiffViewer/DiffViewer";
import CollapsibleUnchanged from "../CollapsibleUnchanged/CollapsibleUnchanged";
import ResultsHeader from "../../../layout/ResultsHeader/ResultsHeader";
import CopySection from "../CopySection/CopySection";
import styles from "./DiffList.module.scss";

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

type VirtuosoItem =
  | {
      type: "HEADER";
      editingMode: EditingMode;
      articleTitle?: string;
      articleUrl?: string;
      sectionTitle?: string;
      changedParagraphs: number;
    }
  | RenderItem
  | { type: "FOOTER"; copied: boolean; onCopyToClipboard: () => void };

interface DiffListProps {
  renderItems: RenderItem[];
  selections: Record<number, Selection>;
  onSelectionChange: (index: number, selection: Selection) => void;
  editingMode: EditingMode;
  articleTitle?: string;
  articleUrl?: string;
  sectionTitle?: string;
  changedParagraphs: number;
  allSelectionsMade: boolean;
  copied: boolean;
  onCopyToClipboard: () => void;
  hideHeader?: boolean;
}

function DiffList({
  renderItems,
  selections,
  onSelectionChange,
  editingMode,
  articleTitle,
  articleUrl,
  sectionTitle,
  changedParagraphs,
  allSelectionsMade,
  copied,
  onCopyToClipboard,
  hideHeader = false,
}: DiffListProps) {
  const virtuosoItems = useMemo((): VirtuosoItem[] => {
    const items: VirtuosoItem[] = [];

    // Add header as first item (unless it's hidden)
    if (!hideHeader) {
      items.push({
        type: "HEADER",
        editingMode,
        articleTitle,
        articleUrl,
        sectionTitle,
        changedParagraphs,
      });
    }

    // Add all render items
    items.push(...renderItems);

    // Add footer if all selections are made
    if (allSelectionsMade) {
      items.push({
        type: "FOOTER",
        copied,
        onCopyToClipboard,
      });
    }

    return items;
  }, [
    renderItems,
    editingMode,
    articleTitle,
    articleUrl,
    sectionTitle,
    changedParagraphs,
    allSelectionsMade,
    copied,
    onCopyToClipboard,
    hideHeader,
  ]);

  const List = useMemo(
    () =>
      forwardRef<
        HTMLDivElement,
        { style?: React.CSSProperties; children?: React.ReactNode }
      >(({ style, children }, ref) => (
        <div ref={ref} className={styles.resultsList} style={style}>
          {children}
        </div>
      )),
    []
  );

  return (
    <Virtuoso
      style={{ height: "100%" }}
      data={virtuosoItems}
      components={{ List }}
      itemContent={(_index, item) => {
        if (item.type === "HEADER") {
          return (
            <ResultsHeader
              editingMode={item.editingMode}
              articleTitle={item.articleTitle}
              articleUrl={item.articleUrl}
              sectionTitle={item.sectionTitle}
              changedParagraphs={item.changedParagraphs}
            />
          );
        } else if (item.type === "FOOTER") {
          return (
            <CopySection
              copied={item.copied}
              onCopyToClipboard={item.onCopyToClipboard}
            />
          );
        } else if (item.type === "CHANGED") {
          return (
            <DiffViewer
              oldValue={item.paragraph.before}
              newValue={item.paragraph.after}
              index={item.originalIndex}
              selection={selections[item.originalIndex]}
              onSelectionChange={onSelectionChange}
            />
          );
        } else {
          return <CollapsibleUnchanged paragraphs={item.paragraphs} />;
        }
      }}
    />
  );
}

export default DiffList;
