import React from 'react'
import SidebarHeader from '../SidebarHeader/SidebarHeader'
import EditingForm from '../EditingForm/EditingForm'
import styles from './Sidebar.module.scss'
import { type EditingMode, type SectionHeading, type ApiKeyConfig } from '../../../utils/api'

interface SidebarProps {
  editingMode: EditingMode
  articleTitle: string
  sectionTitle: string
  availableSections: SectionHeading[]
  loadingSections: boolean
  loading: boolean
  apiKeyConfig: ApiKeyConfig | null
  taskUsedProvider?: string
  taskCreatedAt?: string
  isViewingTask?: boolean
  onModeChange: (mode: EditingMode) => void
  onArticleTitleChange: (title: string) => void
  onSectionTitleChange: (title: string) => void
  onSubmit: (e: React.FormEvent) => void
  onOpenSettings: () => void
}

function Sidebar({
  editingMode,
  articleTitle,
  sectionTitle,
  availableSections,
  loadingSections,
  loading,
  apiKeyConfig,
  taskUsedProvider,
  taskCreatedAt,
  isViewingTask = false,
  onModeChange,
  onArticleTitleChange,
  onSectionTitleChange,
  onSubmit,
  onOpenSettings,
}: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarContent}>
        <SidebarHeader
          apiKeyConfig={apiKeyConfig}
          taskUsedProvider={taskUsedProvider}
          taskCreatedAt={taskCreatedAt}
          isViewingTask={isViewingTask}
          onOpenSettings={onOpenSettings}
        />

        <EditingForm
          editingMode={editingMode}
          onModeChange={onModeChange}
          articleTitle={articleTitle}
          sectionTitle={sectionTitle}
          availableSections={availableSections}
          loadingSections={loadingSections}
          loading={loading}
          disabled={isViewingTask}
          onArticleTitleChange={onArticleTitleChange}
          onSectionTitleChange={onSectionTitleChange}
          onSubmit={onSubmit}
        />
      </div>
    </aside>
  )
}

export default Sidebar
