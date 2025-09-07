import type { ProgressData } from '../../../../utils/api'
import Badge from '../../ui/Badge/Badge'
import styles from './ProgressDisplay.module.scss'

interface ProgressDisplayProps {
  progress: ProgressData
  message?: string
}

function ProgressDisplay({ progress, message = "Processing your edit request..." }: ProgressDisplayProps) {
  const { total_paragraphs, progress_percentage, phase_counts } = progress

  return (
    <div className={styles.progressDisplay}>
      <div className={styles.header}>
        <h3 className={styles.title}>{message}</h3>
        <div className={styles.percentage}>{progress_percentage}%</div>
      </div>

      {/* Progress bar */}
      <div className={styles.progressBar}>
        <div 
          className={styles.progressFill} 
          style={{ width: `${progress_percentage}%` }}
        />
      </div>

      {/* Phase breakdown */}
      <div className={styles.phaseBreakdown}>
        <h4 className={styles.phaseTitle}>Processing Status</h4>
        <div className={styles.phases}>
          {phase_counts.pending > 0 && (
            <div className={styles.phase}>
              <Badge variant="default" size="small">
                {phase_counts.pending} Pending
              </Badge>
            </div>
          )}
          
          {phase_counts.pre_processing > 0 && (
            <div className={styles.phase}>
              <Badge variant="info" size="small">
                {phase_counts.pre_processing} Pre-processing
              </Badge>
            </div>
          )}
          
          {phase_counts.llm_processing > 0 && (
            <div className={styles.phase}>
              <Badge variant="info" size="small">
                {phase_counts.llm_processing} AI Processing
              </Badge>
            </div>
          )}
          
          {phase_counts.post_processing > 0 && (
            <div className={styles.phase}>
              <Badge variant="info" size="small">
                {phase_counts.post_processing} Validating
              </Badge>
            </div>
          )}
          
          {phase_counts.complete > 0 && (
            <div className={styles.phase}>
              <Badge variant="success" size="small">
                {phase_counts.complete} Complete
              </Badge>
            </div>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className={styles.summary}>
        <span className={styles.summaryText}>
          {phase_counts.complete} of {total_paragraphs} paragraphs processed
        </span>
      </div>
    </div>
  )
}

export default ProgressDisplay