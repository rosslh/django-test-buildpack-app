import { useState, useCallback, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../Sidebar/Sidebar'
import MainContent from '../../layout/MainContent/MainContent'
import styles from './EditingInterface.module.scss'
import {
  fetchSectionHeadings,
  editSection,
  pollTaskUntilComplete,
  type SectionHeading,
  type Paragraph,
  type EditResponse,
  type EditingMode,
  type ApiKeyConfig,
  type ProgressData,
} from '../../../utils/api'

type Selection = 'before' | 'after'

type RenderItem =
  | { type: 'CHANGED'; paragraph: Paragraph; originalIndex: number }
  | { type: 'UNCHANGED_GROUP'; paragraphs: Paragraph[]; originalIndex: number }

interface EditingInterfaceProps {
  initialData?: EditResponse | null
  initialArticleTitle?: string
  initialSectionTitle?: string
  isViewingTask?: boolean
  onOpenSettings: () => void
  apiKeyConfig: ApiKeyConfig | null
  taskUsedProvider?: string
  taskCreatedAt?: string
  initialLoading?: boolean
  initialError?: string | null
  loadingMessage?: string
  progressData?: ProgressData | null
}

function EditingInterface({
  initialData,
  initialArticleTitle,
  initialSectionTitle,
  isViewingTask = false,
  onOpenSettings,
  apiKeyConfig,
  taskUsedProvider,
  taskCreatedAt,
  initialLoading = false,
  initialError = null,
  loadingMessage,
  progressData,
}: EditingInterfaceProps) {
  const navigate = useNavigate()
  const [articleTitle, setArticleTitle] = useState(initialArticleTitle || '')
  const [sectionTitle, setSectionTitle] = useState(initialSectionTitle || '')
  const [availableSections, setAvailableSections] = useState<SectionHeading[]>([])
  const [loadingSections, setLoadingSections] = useState(false)
  const [editingMode, setEditingMode] = useState<EditingMode>('copyedit')
  const [loading, setLoading] = useState(initialLoading)
  const [error, setError] = useState<string | null>(initialError)
  const [data, setData] = useState<EditResponse | null>(initialData || null)
  const [selections, setSelections] = useState<Record<number, Selection>>({})
  const [copied, setCopied] = useState(false)

  const fetchSections = useCallback(async (title: string) => {
    if (!title.trim()) {
      setAvailableSections([])
      return
    }

    setLoadingSections(true)
    try {
      const response = await fetchSectionHeadings(title)
      setAvailableSections(response.headings)
    } catch (err) {
      console.error('Failed to fetch sections:', err)
      setAvailableSections([])
    } finally {
      setLoadingSections(false)
    }
  }, [])

  // Update article title when initial prop changes
  useEffect(() => {
    if (initialArticleTitle !== undefined) {
      setArticleTitle(initialArticleTitle)
    }
  }, [initialArticleTitle])

  // Update section title when initial prop changes
  useEffect(() => {
    if (initialSectionTitle !== undefined) {
      setSectionTitle(initialSectionTitle)
    }
  }, [initialSectionTitle])

  // Update loading state when initial prop changes
  useEffect(() => {
    setLoading(initialLoading)
  }, [initialLoading])

  // Update error state when initial prop changes
  useEffect(() => {
    setError(initialError)
  }, [initialError])

  // Update data when initial prop changes
  useEffect(() => {
    setData(initialData || null)
  }, [initialData])

  // Fetch sections when article title changes (only if not viewing a task)
  useEffect(() => {
    if (!isViewingTask) {
      const debounceTimer = setTimeout(() => {
        fetchSections(articleTitle)
      }, 500)

      return () => clearTimeout(debounceTimer)
    }
  }, [articleTitle, fetchSections, isViewingTask])

  // Set initial selections when data is loaded
  useEffect(() => {
    if (data) {
      const defaultSelections: Record<number, Selection> = {}
      data.paragraphs.forEach((paragraph: Paragraph, index: number) => {
        if (paragraph.status === 'CHANGED') {
          defaultSelections[index] = 'before'
        }
      })
      setSelections(defaultSelections)
    }
  }, [data])

  const renderItems = useMemo(() => {
    if (!data) return []

    const items: RenderItem[] = []
    let unchangedGroup: Paragraph[] = []
    let firstUnchangedIndex = -1

    data.paragraphs.forEach((p: Paragraph, index: number) => {
      if (p.status === 'CHANGED') {
        if (unchangedGroup.length > 0) {
          items.push({
            type: 'UNCHANGED_GROUP',
            paragraphs: unchangedGroup,
            originalIndex: firstUnchangedIndex,
          })
          unchangedGroup = []
          firstUnchangedIndex = -1
        }
        items.push({
          type: 'CHANGED',
          paragraph: p,
          originalIndex: index,
        })
      } else {
        if (firstUnchangedIndex === -1) {
          firstUnchangedIndex = index
        }
        unchangedGroup.push(p)
      }
    })

    if (unchangedGroup.length > 0) {
      items.push({
        type: 'UNCHANGED_GROUP',
        paragraphs: unchangedGroup,
        originalIndex: firstUnchangedIndex,
      })
    }

    return items
  }, [data])

  const handleSelectionChange = useCallback((index: number, selection: Selection) => {
    setSelections((prev) => ({ ...prev, [index]: selection }))
    setCopied(false)
  }, [])

  const handleModeChange = useCallback((mode: EditingMode) => {
    setEditingMode(mode)
    // Reset results when mode changes (only if not viewing a task)
    if (!isViewingTask) {
      setData(null)
      setSelections({})
      setCopied(false)
      setError(null)
    }
  }, [isViewingTask])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!articleTitle.trim()) {
      setError('Article title is required.')
      return
    }
    if (!sectionTitle.trim()) {
      setError('Section title is required.')
      return
    }
    if (!apiKeyConfig) {
      setError('Please configure your API key in settings.')
      return
    }

    setLoading(true)
    setError(null)
    setData(null)
    setSelections({})
    setCopied(false)

    try {
      const task = await editSection(editingMode, articleTitle, sectionTitle, apiKeyConfig)
      
      // If not viewing a task, redirect immediately to the results page
      if (!isViewingTask) {
        navigate(`/task/${task.task_id}`)
        return
      }
      
      // If viewing a task, continue with the old behavior (poll and display results)
      const response = await pollTaskUntilComplete(task.task_id)
      setData(response)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
        console.error(err)
      } else {
        setError('Failed to edit section. Please check the article title and section title and try again.')
        console.error(err)
      }
    } finally {
      setLoading(false)
    }
  }

  const changedParagraphs = data?.paragraphs.filter((p: Paragraph) => p.status === 'CHANGED').length || 0
  const allSelectionsMade = Object.keys(selections).length === changedParagraphs

  const handleCopyToClipboard = () => {
    if (!data) return

    const finalText = data.paragraphs
      .map((p: Paragraph, index: number) => {
        if (p.status === 'CHANGED') {
          const selection = selections[index]
          return selection === 'after' ? p.after : p.before
        } else {
          return p.before
        }
      })
      .join('\n\n')

    navigator.clipboard.writeText(finalText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={styles.editingInterface}>
      <Sidebar
        editingMode={editingMode}
        articleTitle={articleTitle}
        sectionTitle={sectionTitle}
        availableSections={availableSections}
        loadingSections={loadingSections}
        loading={loading}
        apiKeyConfig={apiKeyConfig}
        taskUsedProvider={taskUsedProvider}
        taskCreatedAt={taskCreatedAt}
        isViewingTask={isViewingTask}
        onModeChange={handleModeChange}
        onArticleTitleChange={setArticleTitle}
        onSectionTitleChange={setSectionTitle}
        onSubmit={handleSubmit}
        onOpenSettings={onOpenSettings}
      />

      <MainContent
        data={data}
        loading={loading}
        error={error}
        editingMode={editingMode}
        selections={selections}
        copied={copied}
        changedParagraphs={changedParagraphs}
        allSelectionsMade={allSelectionsMade}
        renderItems={renderItems}
        onSelectionChange={handleSelectionChange}
        onCopyToClipboard={handleCopyToClipboard}
        loadingMessage={loadingMessage}
        progressData={progressData}
        isViewingTask={isViewingTask}
      />
    </div>
  )
}

export default EditingInterface