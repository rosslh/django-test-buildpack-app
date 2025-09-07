import { useState, useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import EditingInterface from '../../editing/EditingInterface/EditingInterface'
import EditHistoryPage from '../../tasks/EditHistoryPage/EditHistoryPage'
import TaskViewPage from '../../tasks/TaskViewPage/TaskViewPage'
import SettingsModal from '../../shared/components/SettingsModal/SettingsModal'
import InfoModal from '../../shared/components/InfoModal/InfoModal'
import { Navbar } from '../Navbar'
import styles from './App.module.scss'
import { type ApiKeyConfig } from '../../../utils/api'

// LocalStorage key for API configuration
const API_CONFIG_KEY = 'editengine-api-config'

// Helper functions for localStorage
const saveApiConfig = (config: ApiKeyConfig) => {
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify(config))
}

const loadApiConfig = (): ApiKeyConfig | null => {
  try {
    const stored = localStorage.getItem(API_CONFIG_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function App() {
  const [apiKeyConfig, setApiKeyConfig] = useState<ApiKeyConfig | null>(null)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [infoModalProvider, setInfoModalProvider] = useState<string | null>(null)

  // Load API configuration from localStorage on mount
  useEffect(() => {
    const config = loadApiConfig()
    setApiKeyConfig(config)
  }, [])

  const handleSaveApiConfig = (config: ApiKeyConfig) => {
    setApiKeyConfig(config)
    saveApiConfig(config)
  }

  const handleOpenSettings = () => {
    setIsSettingsModalOpen(true)
  }

  const handleCloseSettings = () => {
    setIsSettingsModalOpen(false)
  }

  const handleShowInfo = (provider: string) => {
    setIsSettingsModalOpen(false)
    setInfoModalProvider(provider)
  }

  const handleCloseInfo = () => {
    setInfoModalProvider(null)
    setIsSettingsModalOpen(true)
  }

  return (
    <div className={styles.app}>
      <Navbar />
      <div className={styles.mainContent}>
        <Routes>
        <Route 
          path="/" 
          element={
            <EditingInterface
              onOpenSettings={handleOpenSettings}
              apiKeyConfig={apiKeyConfig}
            />
          } 
        />
        <Route path="/history" element={<EditHistoryPage />} />
        <Route 
          path="/task/:taskId" 
          element={
            <TaskViewPage
              onOpenSettings={handleOpenSettings}
              apiKeyConfig={apiKeyConfig}
            />
          } 
        />
        </Routes>
      </div>

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={handleCloseSettings}
        onSave={handleSaveApiConfig}
        onShowInfo={handleShowInfo}
        currentConfig={apiKeyConfig}
      />

      <InfoModal
        isOpen={!!infoModalProvider}
        onClose={handleCloseInfo}
        provider={infoModalProvider || ''}
      />
    </div>
  )
}

export default App