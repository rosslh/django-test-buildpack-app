import React, { useMemo, memo } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import CheckCircle from '~icons/custom/check-circle';
import Icon from '../../ui/Icon/Icon';
import { processWrappableUrls } from '../../../../utils/urlUtils';
import styles from './DiffViewer.module.scss';

type Selection = 'before' | 'after';

interface DiffViewerProps {
  oldValue: string;
  newValue: string;
  index: number;
  selection: Selection | undefined;
  onSelectionChange: (index: number, selection: Selection) => void;
}

// Function to read CSS variable from root element
const getCSSVariable = (variableName: string): string => {
  return getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
};

const DiffViewer: React.FC<DiffViewerProps> = ({ oldValue, newValue, index, selection, onSelectionChange }) => {
  const [processedOldValue, processedNewValue] = useMemo(() => {
    return processWrappableUrls(oldValue, newValue);
  }, [oldValue, newValue]);

  // Create custom styles using design tokens
  const customStyles = useMemo(() => ({
    variables: {
      light: {
        // Background and text colors
        diffViewerBackground: 'transparent',
        diffViewerColor: getCSSVariable('--color-gray-900'),

        // Added (green) colors - custom for diff
        addedBackground: 'unset',
        addedColor: getCSSVariable('--color-gray-900'),
        wordAddedBackground: getCSSVariable('--color-green-200'),

        // Removed (red) colors - custom for diff
        removedBackground: 'unset',
        removedColor: getCSSVariable('--color-gray-900'),
        wordRemovedBackground: getCSSVariable('--color-red-200'),

        // Empty lines
        emptyLineBackground: 'transparent',

        // Title block
        diffViewerTitleBackground: 'transparent',
        diffViewerTitleColor: 'inherit',
        diffViewerTitleBorderColor: getCSSVariable('--color-gray-200'),
      },
    },
    // Style objects using design tokens
    diffContainer: {
      fontFamily: getCSSVariable('--font-family-code'),
      fontSize: getCSSVariable('--font-size-small'),
      borderRadius: 0,
      position: 'relative',
      border: 'none',

    },
    titleBlock: {
      fontSize: getCSSVariable('--font-size-small'),
      fontWeight: getCSSVariable('--font-weight-semibold'),
      padding: `0 ${getCSSVariable('--spacing-12')}`,
    },
    contentText: {
      fontFamily: getCSSVariable('--font-family-code'),
      fontSize: getCSSVariable('--font-size-small'),
      fontWeight: getCSSVariable('--font-weight-normal'),
      padding: `${getCSSVariable('--spacing-16')} ${getCSSVariable('--spacing-16')}`,
      lineHeight: `${getCSSVariable('--line-height-normal')} !important`,
    },
    wordDiff: {
      display: 'inline',
      wordBreak: 'normal',
      borderRadius: getCSSVariable('--radius-4'),
      padding: "0"
    },
  }), []);

  const handleLeftClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectionChange(index, 'before');
  };

  const handleRightClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSelectionChange(index, 'after');
  };

  // Determine title container classes
  const leftTitleClass = `${styles.titleContainer} ${selection === 'before' ? styles.selectedTitle : ''}`;
  const rightTitleClass = `${styles.titleContainer} ${selection === 'after' ? styles.selectedTitle : ''}`;

  return (
    <div className={`${styles.container} ${selection === 'before' ? styles.selectedBefore : ''} ${selection === 'after' ? styles.selectedAfter : ''}`}>
      <div className={styles.splitViewContainer}>
        <ReactDiffViewer
          oldValue={processedOldValue}
          newValue={processedNewValue}
          splitView={true}
          useDarkTheme={false}
          showDiffOnly={false}
          leftTitle={
            <div className={leftTitleClass}>
              <span className={styles.titleText}>
                Original
                {selection === 'before' && (
                  <Icon
                    icon={CheckCircle}
                    size={16}
                    color="secondary"
                    className={styles.selectionIndicator}
                  />
                )}
              </span>
            </div>
          }
          rightTitle={
            <div className={rightTitleClass}>
              <span className={styles.titleText}>
                AI Edit
                {selection === 'after' && (
                  <Icon
                    icon={CheckCircle}
                    size={16}
                    color="primary"
                    className={styles.selectionIndicator}
                  />
                )}
              </span>
            </div>
          }
          hideLineNumbers={true}
          hideMarkers={true}
          styles={customStyles}
          compareMethod={DiffMethod.WORDS}
        />

        {/* Click overlay for left side */}
        <div
          className={`${styles.clickOverlay} ${styles.leftOverlay}`}
          onClick={handleLeftClick}
        />

        {/* Click overlay for right side */}
        <div
          className={`${styles.clickOverlay} ${styles.rightOverlay}`}
          onClick={handleRightClick}
        />
      </div>
    </div>
  );
};

// Memoize the component to prevent unnecessary re-renders when props haven't changed
export default memo(DiffViewer);
