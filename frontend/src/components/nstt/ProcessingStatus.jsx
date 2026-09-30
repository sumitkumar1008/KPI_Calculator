import React from 'react'
import './ProcessingStatus.css'

export const NSTT_PIPELINE_STEPS = [
  { id: 'namo_loaded', label: 'Namo file loaded' },
  { id: 'remedy_loaded', label: 'Remedy file loaded' },
  { id: 'columns_validated', label: 'Required columns validated' },
  { id: 'vlookup_completed', label: 'VLOOKUP completed (Left Join on INCIDENTID)' },
  { id: 'impact_converted', label: 'INCIDENT_IMPACT converted (0→SA, 1→NSA)' },
  { id: 'enriched_created', label: 'Final enriched dataset created' },
  { id: 'duplicate_checked', label: 'Duplicate validation completed' },
  { id: 'master_generated', label: 'Master Response JSON generated' },
  { id: 'logic_processing', label: 'NSTT Rule Engine logic processing' },
  { id: 'dashboard_aggregated', label: 'Dashboard aggregation & metrics calculated' },
]

export default function ProcessingStatus({
  currentStep = 0,
  stepStates = {},
  isComplete = false,
  hasError = false,
  errorMessage = null,
  namoFileName = '',
  remedyFileName = '',
  stats = null,
  onReset = null,
}) {
  const totalSteps = NSTT_PIPELINE_STEPS.length
  const completedCount = isComplete
    ? totalSteps
    : hasError
    ? Math.max(0, currentStep)
    : currentStep

  const percent = Math.min(100, Math.round((completedCount / totalSteps) * 100))

  return (
    <div className="processing-status-card" role="region" aria-label="NSTT Processing Status">
      <div className="status-card-header">
        <div className="status-header-text">
          <span className="status-tag">Pipeline Execution</span>
          <h3>Processing NSTT Analytics Data</h3>
          <p className="status-subtext">
            {isComplete ? (
              <span className="text-success font-medium">✓ Pipeline finished successfully</span>
            ) : hasError ? (
              <span className="text-error font-medium">✗ Processing stopped with an error</span>
            ) : (
              <span>Correlating datasets: <strong>{namoFileName || 'Namo'}</strong> + <strong>{remedyFileName || 'Remedy'}</strong></span>
            )}
          </p>
        </div>
        <div className="status-badge-container">
          <span className={`status-pill ${isComplete ? 'complete' : hasError ? 'error' : 'running'}`}>
            {isComplete ? 'Complete (100%)' : hasError ? 'Failed' : `Step ${Math.min(currentStep + 1, totalSteps)} of ${totalSteps}`}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-wrapper">
        <div
          className={`progress-bar-fill ${isComplete ? 'is-complete' : hasError ? 'is-error' : 'is-running'}`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* 10-Step Timeline */}
      <ul className="pipeline-steps-list">
        {NSTT_PIPELINE_STEPS.map((step, idx) => {
          let state = 'pending'
          if (stepStates[step.id]) {
            state = stepStates[step.id]
          } else if (idx < currentStep || isComplete) {
            state = 'complete'
          } else if (idx === currentStep && !hasError) {
            state = 'active'
          } else if (idx === currentStep && hasError) {
            state = 'error'
          }

          return (
            <li key={step.id} className={`pipeline-step-item state-${state}`}>
              <div className="step-indicator">
                {state === 'complete' && (
                  <span className="step-icon step-icon-complete" aria-hidden="true">✓</span>
                )}
                {state === 'active' && (
                  <span className="step-spinner" aria-hidden="true" />
                )}
                {state === 'error' && (
                  <span className="step-icon step-icon-error" aria-hidden="true">✗</span>
                )}
                {state === 'pending' && (
                  <span className="step-icon step-icon-pending" aria-hidden="true">○</span>
                )}
              </div>
              <div className="step-details">
                <span className="step-number">Step {idx + 1}</span>
                <span className="step-label">{step.label}</span>
              </div>
            </li>
          )
        })}
      </ul>

      {/* Error display */}
      {hasError && errorMessage && (
        <div className="status-error-box" role="alert">
          <div className="error-icon-circle">!</div>
          <div className="error-content">
            <h4>Processing Error</h4>
            <p>{errorMessage}</p>
          </div>
          {onReset && (
            <button type="button" className="retry-btn" onClick={onReset}>
              Try Again
            </button>
          )}
        </div>
      )}

      {/* Success Summary Info */}
      {isComplete && stats && (
        <div className="status-stats-ribbon">
          <div className="stat-pill">
            <span className="stat-label">Namo Records:</span>
            <span className="stat-val">{stats.namo_rows?.toLocaleString() || 0}</span>
          </div>
          <div className="stat-pill">
            <span className="stat-label">Remedy Records:</span>
            <span className="stat-val">{stats.remedy_rows?.toLocaleString() || 0}</span>
          </div>
          <div className="stat-pill">
            <span className="stat-label">Matched:</span>
            <span className="stat-val">{stats.matched?.toLocaleString() || 0}</span>
          </div>
          {stats.unmatched > 0 && (
            <div className="stat-pill stat-warning">
              <span className="stat-label">Unmatched:</span>
              <span className="stat-val">{stats.unmatched}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
