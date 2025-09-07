import { useState, useEffect } from 'react'
import Modal from '../Modal/Modal'
import Icon from '../../ui/Icon/Icon'
import InfoIcon from '~icons/custom/info'
import styles from './SettingsModal.module.scss'
import { type ApiProvider, type ApiKeyConfig } from '../../../../utils/api'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (config: ApiKeyConfig) => void
  onShowInfo: (provider: string) => void
  currentConfig: ApiKeyConfig | null
}

function SettingsModal({ isOpen, onClose, onSave, onShowInfo, currentConfig }: SettingsModalProps) {
  const [provider, setProvider] = useState<ApiProvider>('google')
  const [apiKeys, setApiKeys] = useState<ApiKeyConfig>({
    provider: 'google',
    google: '',
    openai: '',
    anthropic: '',
    mistral: '',
    perplexity: ''
  })
  const [showApiKey, setShowApiKey] = useState(false)

  // Initialize form with current config when modal opens
  useEffect(() => {
    if (isOpen && currentConfig) {
      setApiKeys({
        provider: currentConfig.provider,
        google: currentConfig.google || '',
        openai: currentConfig.openai || '',
        anthropic: currentConfig.anthropic || '',
        mistral: currentConfig.mistral || '',
        perplexity: currentConfig.perplexity || ''
      })

      setProvider(currentConfig.provider)
    } else if (isOpen && !currentConfig) {
      setApiKeys({
        provider: 'google',
        google: '',
        openai: '',
        anthropic: '',
        mistral: '',
        perplexity: ''
      })
      setProvider('google')
    }
  }, [isOpen, currentConfig])

  const handleSave = () => {
    const currentApiKey = apiKeys[provider]
    if (!currentApiKey?.trim()) {
      return
    }

    // Save the configuration including the selected provider
    const configToSave = {
      provider,
      google: apiKeys.google,
      openai: apiKeys.openai,
      anthropic: apiKeys.anthropic,
      mistral: apiKeys.mistral,
      perplexity: apiKeys.perplexity
    }

    onSave(configToSave)
    onClose()
  }

  const handleClose = () => {
    // Reset form when closing without saving
    if (currentConfig) {
      setApiKeys({
        provider: currentConfig.provider,
        google: currentConfig.google || '',
        openai: currentConfig.openai || '',
        anthropic: currentConfig.anthropic || '',
        mistral: currentConfig.mistral || '',
        perplexity: currentConfig.perplexity || ''
      })
    } else {
      setApiKeys({
        provider: 'google',
        google: '',
        openai: '',
        anthropic: '',
        mistral: '',
        perplexity: ''
      })
    }
    onClose()
  }

  const handleApiKeyChange = (value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [provider]: value
    }))
  }

  const handleInfoClick = (providerName: string) => {
    onShowInfo(providerName)
  }

  const currentApiKey = apiKeys[provider] || ''

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="API Settings"
      secondaryButton={{
        text: 'Cancel',
        onClick: handleClose
      }}
      primaryButton={{
        text: 'Save Settings',
        onClick: handleSave,
        disabled: !currentApiKey.trim()
      }}
    >
      <div className={styles.content}>
        <div className={styles.section}>
          <label className={styles.sectionLabel}>AI Provider</label>
          <div className={styles.radioGroup}>
            <label className={styles.radioOption}>
              <input
                type="radio"
                value="google"
                checked={provider === 'google'}
                onChange={(e) => setProvider(e.target.value as ApiProvider)}
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>Google (Gemini)</span>
              <button
                type="button"
                onClick={() => handleInfoClick('google')}
                className={styles.infoButton}
                aria-label="Get Google API key guide"
              >
                <Icon icon={InfoIcon} size={16} color="secondary" />
              </button>
            </label>
            <label className={styles.radioOption}>
              <input
                type="radio"
                value="openai"
                checked={provider === 'openai'}
                onChange={(e) => setProvider(e.target.value as ApiProvider)}
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>OpenAI (GPT)</span>
              <button
                type="button"
                onClick={() => handleInfoClick('openai')}
                className={styles.infoButton}
                aria-label="Get OpenAI API key guide"
              >
                <Icon icon={InfoIcon} size={16} color="secondary" />
              </button>
            </label>
            <label className={styles.radioOption}>
              <input
                type="radio"
                value="anthropic"
                checked={provider === 'anthropic'}
                onChange={(e) => setProvider(e.target.value as ApiProvider)}
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>Anthropic (Claude)</span>
              <button
                type="button"
                onClick={() => handleInfoClick('anthropic')}
                className={styles.infoButton}
                aria-label="Get Anthropic API key guide"
              >
                <Icon icon={InfoIcon} size={16} color="secondary" />
              </button>
            </label>
            <label className={styles.radioOption}>
              <input
                type="radio"
                value="mistral"
                checked={provider === 'mistral'}
                onChange={(e) => setProvider(e.target.value as ApiProvider)}
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>Mistral</span>
              <button
                type="button"
                onClick={() => handleInfoClick('mistral')}
                className={styles.infoButton}
                aria-label="Get Mistral API key guide"
              >
                <Icon icon={InfoIcon} size={16} color="secondary" />
              </button>
            </label>
            <label className={styles.radioOption}>
              <input
                type="radio"
                value="perplexity"
                checked={provider === 'perplexity'}
                onChange={(e) => setProvider(e.target.value as ApiProvider)}
                className={styles.radioInput}
              />
              <span className={styles.radioLabel}>Perplexity</span>
              <button
                type="button"
                onClick={() => handleInfoClick('perplexity')}
                className={styles.infoButton}
                aria-label="Get Perplexity API key guide"
              >
                <Icon icon={InfoIcon} size={16} color="secondary" />
              </button>
            </label>
          </div>
        </div>

        <div className={styles.section}>
          <label htmlFor="apiKey" className={styles.sectionLabel}>
            API Key
          </label>
          <div className={styles.inputWrapper}>
            <input
              id="apiKey"
              type={showApiKey ? 'text' : 'password'}
              value={currentApiKey}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              placeholder={`Enter your ${
                provider === 'google' ? 'Google' :
                provider === 'openai' ? 'OpenAI' :
                provider === 'anthropic' ? 'Anthropic' :
                provider === 'mistral' ? 'Mistral' :
                'Perplexity'
              } API key`}
              className={styles.input}
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className={styles.toggleButton}
              aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
            >
              {showApiKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p className={styles.helpText}>
            {provider === 'google' && 'Get your API key from Google AI Studio'}
            {provider === 'openai' && 'Get your API key from OpenAI Dashboard'}
            {provider === 'anthropic' && 'Get your API key from Anthropic Console'}
            {provider === 'mistral' && 'Get your API key from Mistral Console'}
            {provider === 'perplexity' && 'Get your API key from Perplexity Dashboard'}
          </p>
        </div>
      </div>
    </Modal>
  )
}

export default SettingsModal
