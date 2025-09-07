import styles from './CopySection.module.scss'
import CheckCircle from '~icons/custom/check-circle'
import Check from '~icons/custom/check'
import Icon from '../../ui/Icon/Icon'

interface CopySectionProps {
  copied: boolean
  onCopyToClipboard: () => void
}

function CopySection({ copied, onCopyToClipboard }: CopySectionProps) {
  return (
    <div className={styles.copySection}>
      <div className={styles.copySectionInner}>
        <div className={styles.copyIconWrapper}>
          <div className={styles.copyIcon}>
            <Icon icon={CheckCircle} size={24} color="secondary" />
          </div>
        </div>
        <h3 className={styles.copyTitle}>Ready to Copy!</h3>
        <p className={styles.copyDescription}>You've reviewed all changes. Click below to copy the final article to your clipboard.</p>
        <button
          onClick={onCopyToClipboard}
          className={styles.copyButton}
        >
          {copied ? (
            <div className={styles.flexCenter}>
              <Icon icon={Check} size={20} color="primary" className={styles.copyButtonIcon} />
              Copied!
            </div>
          ) : (
            'Copy Final Article to Clipboard'
          )}
        </button>
      </div>
    </div>
  )
}

export default CopySection
