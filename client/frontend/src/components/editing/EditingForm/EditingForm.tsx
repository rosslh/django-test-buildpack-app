import React from 'react'
import Combobox from '../../shared/components/Combobox/Combobox'
import Spinner from '../../shared/ui/Spinner/Spinner'
import Button from '../../shared/ui/Button/Button'
import styles from './EditingForm.module.scss'

type EditingMode = 'brevity' | 'copyedit'

interface SectionHeading {
  text: string
  level: number
}

interface EditingFormProps {
  editingMode: EditingMode
  articleTitle: string
  sectionTitle: string
  availableSections: SectionHeading[]
  loadingSections: boolean
  loading: boolean
  disabled?: boolean
  onArticleTitleChange: (title: string) => void
  onSectionTitleChange: (title: string) => void
  onSubmit: (e: React.FormEvent) => void
  onModeChange: (mode: EditingMode) => void
}

function EditingForm({
  editingMode,
  articleTitle,
  sectionTitle,
  availableSections,
  loadingSections,
  loading,
  disabled = false,
  onArticleTitleChange,
  onSectionTitleChange,
  onSubmit,
  onModeChange,
}: EditingFormProps) {
  const getModeDescription = (mode: EditingMode) => {
    if (mode === 'brevity') {
      return 'Make content more concise and remove unnecessary words'
    }
    return 'Improve grammar, style, and clarity while preserving meaning'
  }

  return (
    <form onSubmit={onSubmit} className={styles.form}>
      <div className={styles.inputWrapper}>
        <label htmlFor="articleTitle" className={styles.inputLabel}>
          Wikipedia Article Title
        </label>
        <input
          id="articleTitle"
          type="text"
          value={articleTitle}
          onChange={(e) => onArticleTitleChange(e.target.value)}
          placeholder="e.g., 'Apollo', 'Climate change'"
          className={styles.input}
          disabled={loading || disabled}
        />
      </div>
      <div className={styles.inputWrapper}>
        <label htmlFor="sectionTitle" className={styles.inputLabel}>
          Section Title
        </label>
        <Combobox
          id="sectionTitle"
          value={sectionTitle}
          onChange={onSectionTitleChange}
          options={availableSections.map(section => ({
            value: section.text,
            label: section.text
          }))}
          loading={loadingSections}
          disabled={loading || disabled}
          emptyStateText="No sections found"
          loadingStateText="Loading sections..."
          className={styles.input}
          hasPrerequisite={articleTitle.trim().length >= 3}
        />
      </div>

      <div className={styles.modeToggle}>
        <div className={styles.modeToggleLabel}>
          <span className={styles.modeToggleTitle}>Editing Mode</span>
        </div>
        <div className={styles.modeToggleButtons}>
          <button
            type="button"
            onClick={() => onModeChange('copyedit')}
            className={`${styles.modeButton} ${editingMode === 'copyedit' ? styles.modeButtonActive : ''}`}
            disabled={loading || disabled}
          >
            General Copyedit
          </button>
          <button
            type="button"
            onClick={() => onModeChange('brevity')}
            className={`${styles.modeButton} ${editingMode === 'brevity' ? styles.modeButtonActive : ''}`}
            disabled={loading || disabled}
          >
            Brevity
          </button>
        </div>
        <span className={styles.modeToggleDescription}>{getModeDescription(editingMode)}</span>
      </div>

      <Button
        type="submit"
        variant="primary"
        disabled={loading || disabled}
      >
        {loading ? (
          <div className={styles.flexCenter}>
            <Spinner
              size={20}
              color="on-primary"
              className={styles.loadingIcon}
            />
            {editingMode === 'brevity' ? 'Generating...' : 'Editing...'}
          </div>
        ) : disabled ? (
          'View Results'
        ) : (
          'Generate Edits'
        )}
      </Button>
    </form>
  )
}

export default EditingForm
