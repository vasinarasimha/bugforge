import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import {
  startTroubleshooting,
  submitTroubleshootingAnswer,
  confirmTroubleshooting,
  cancelTroubleshooting
} from '../../services/aiService'

export default function TroubleshootingModal({
  payload, // The defect draft
  onConfirm, // Called when issue is successfully created with AI data
  onSkip, // Called when user skips analysis
  onClose
}) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isConfirmingRef = useRef(false)
  const isSkippingRef = useRef(false)

  // Current question data
  const [questionData, setQuestionData] = useState(null)
  // Answer data
  const [selectedOption, setSelectedOption] = useState('') // For single/multiple choice
  const [textAnswer, setTextAnswer] = useState('')
  const [multiSelect, setMultiSelect] = useState([])

  useEffect(() => {
    // Start session when component mounts
    let isMounted = true
    const initSession = async () => {
      console.log("[TroubleshootingModal] Starting session with payload:", payload)
      try {
        const { data } = await startTroubleshooting(payload)
        console.log("[TroubleshootingModal] Session started successfully:", data)
        if (isMounted) {
          setSession(data)
          if (data.status === 'questioning') {
            setQuestionData(data)
          }
          setLoading(false)
        }
      } catch (err) {
        console.error("[TroubleshootingModal] Error starting session:", err)
        if (isMounted) {
          setError(err.response?.data?.detail || 'The AI troubleshooting service is temporarily unavailable. You can retry or skip analysis.')
          setLoading(false)
        }
      }
    }
    initSession()

    return () => {
      isMounted = false
    }
  }, [payload])

  const handleCancel = async () => {
    console.log("[TroubleshootingModal] handleCancel called")
    if (session && session.session_id && (session.status === 'questioning' || session.status === 'started')) {
      try {
        await cancelTroubleshooting(session.session_id)
        console.log("[TroubleshootingModal] Session cancelled successfully")
      } catch (e) {
        console.error("[TroubleshootingModal] Failed to cancel session on close:", e)
      }
    }
    onClose()
  }

  const handleSkip = () => {
    if (isSkippingRef.current || isConfirmingRef.current || loading) return
    isSkippingRef.current = true
    console.log("[TroubleshootingModal] handleSkip called, bypassing AI")
    handleCancel()
    onSkip()
  }

  const handleSubmitAnswer = async () => {
    if (loading) return
    if (!session || !questionData) return

    let answerStr = ''
    if (questionData.question_type === 'multiple_choice' || questionData.question_type === 'yes_no' || questionData.question_type === 'single_select') {
      if (!selectedOption) return setError('Please select an option.')
      const opt = questionData.options?.find(o => o.id === selectedOption)
      answerStr = opt ? `${opt.id}: ${opt.label}` : selectedOption
    } else if (questionData.question_type === 'multi_select') {
      if (multiSelect.length === 0) return setError('Please select at least one option.')
      const opts = questionData.options?.filter(o => multiSelect.includes(o.id)) || []
      answerStr = opts.map(o => `${o.id}: ${o.label}`).join(', ')
    } else {
      if (!textAnswer.trim()) return setError('Please provide an answer.')
      answerStr = textAnswer.trim()
    }

    console.log(`[TroubleshootingModal] Submitting answer for Q${questionData.question_number}:`, answerStr)

    setLoading(true)
    setError('')
    try {
      const { data } = await submitTroubleshootingAnswer(session.session_id, {
        question_number: questionData.question_number,
        answer: answerStr
      })
      
      console.log("[TroubleshootingModal] Received next step:", data)

      // Reset inputs ONLY on success
      setSelectedOption('')
      setTextAnswer('')
      setMultiSelect([])

      setSession(data)
      if (data.status === 'questioning') {
        setQuestionData(data)
      }
    } catch (err) {
      console.error("[TroubleshootingModal] Error submitting answer:", err)
      // Keep existing questionData and user's answer visible for retry
      setError(err.response?.data?.detail || 'The AI could not process your answer right now. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmAndCreate = async () => {
    if (isConfirmingRef.current || isSkippingRef.current || loading) return
    isConfirmingRef.current = true
    console.log("[TroubleshootingModal] handleConfirmAndCreate called")
    setLoading(true)
    setError('')
    try {
      const { data } = await confirmTroubleshooting(session.session_id, payload)
      console.log("[TroubleshootingModal] Issue created with AI root cause:", data)
      onConfirm(data)
    } catch (err) {
      isConfirmingRef.current = false
      console.error("[TroubleshootingModal] Error confirming issue:", err)
      setError(err.response?.data?.detail || 'Failed to create issue.')
      setLoading(false)
    }
  }

  const renderDots = () => {
    const total = 10
    const current = questionData?.question_number || (session?.question_number || (session?.question_count || 0) + 1)
    const dots = []
    for (let i = 1; i <= total; i++) {
      let className = 'tm-dot'
      if (session?.status === 'confirmed' || session?.status === 'insufficient_evidence') {
        if (i <= current) className += ' completed'
      } else {
        if (i < current) className += ' completed'
        else if (i === current && session?.status === 'questioning') className += ' active'
      }
      
      dots.push(<div key={i} className={className} />)
    }
    return <div className="tm-progress-dots">{dots}</div>
  }

  const toggleMultiSelect = (id) => {
    if (loading) return
    setMultiSelect(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const renderQuestionInput = () => {
    if (!questionData) return null

    if (questionData.question_type === 'text') {
      return (
        <textarea
          className="tm-textarea"
          rows={4}
          value={textAnswer}
          disabled={loading}
          autoComplete="off"
          onChange={(e) => setTextAnswer(e.target.value)}
          placeholder="Type your answer here..."
          autoFocus
        />
      )
    }

    if (questionData.question_type === 'multi_select') {
      return (
        <div className="tm-options">
          {questionData.options?.map(opt => (
            <label key={opt.id} className={`tm-option-label ${multiSelect.includes(opt.id) ? 'selected' : ''}`}>
              <input 
                type="checkbox"
                checked={multiSelect.includes(opt.id)}
                disabled={loading}
                onChange={() => toggleMultiSelect(opt.id)}
              />
              <span className="tm-option-text"><strong>{opt.id}</strong>: {opt.label}</span>
            </label>
          ))}
        </div>
      )
    }

    // Default to single select radio buttons
    return (
      <div className="tm-options">
        {questionData.options?.map(opt => (
          <label key={opt.id} className={`tm-option-label ${selectedOption === opt.id ? 'selected' : ''}`}>
            <input 
              type="radio"
              name="single_choice"
              value={opt.id}
              checked={selectedOption === opt.id}
              disabled={loading}
              onChange={() => setSelectedOption(opt.id)}
            />
            <span className="tm-option-text"><strong>{opt.id}</strong>: {opt.label}</span>
          </label>
        ))}
      </div>
    )
  }

  const renderContent = () => {
    if (loading && !session && !questionData) {
      return (
        <div className="tm-loading-state">
          <div className="tm-spinner"></div>
          <p>Initializing AI Root-Cause Analysis...</p>
        </div>
      )
    }

    if (session?.status === 'confirmed') {
      return (
        <div className="tm-result-card tm-success">
          <div className="tm-result-icon">✅</div>
          <h3 className="tm-result-title">Root Cause Confirmed</h3>
          <div className="tm-result-confidence">Confidence: {Math.round((session.confidence || 0.85) * 100)}%</div>
          
          <div className="tm-result-section">
            <h4>Identified Root Cause</h4>
            <p>{session.root_cause}</p>
          </div>

          {session.evidence && session.evidence.length > 0 && (
            <div className="tm-result-section">
              <h4>Supporting Evidence</h4>
              <ul>
                {session.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
              </ul>
            </div>
          )}

          {session.recommended_fix && (
            <div className="tm-result-section">
              <h4>Recommended Fix / Remediation</h4>
              <p>{session.recommended_fix}</p>
            </div>
          )}
        </div>
      )
    }

    if (session?.status === 'insufficient_evidence') {
      return (
        <div className="tm-result-card tm-warning">
          <div className="tm-result-icon">⚠️</div>
          <h3 className="tm-result-title">Investigation Concluded (Preliminary Findings)</h3>
          <div className="tm-result-confidence">Confidence: {Math.round((session.confidence || 0.50) * 100)}%</div>
          <p style={{marginBottom: '16px', color: '#64748b', fontSize: '0.9rem'}}>
            Maximum diagnostic questions reached without full certainty. Below is the most probable cause based on the reported observations.
          </p>

          <div className="tm-result-section">
            <h4>Suspected Root Cause</h4>
            <p>{session.root_cause}</p>
          </div>

          {session.evidence && session.evidence.length > 0 && (
            <div className="tm-result-section">
              <h4>Observations Noted</h4>
              <ul>
                {session.evidence.map((ev, i) => <li key={i}>{ev}</li>)}
              </ul>
            </div>
          )}

          {session.recommended_fix && (
            <div className="tm-result-section">
              <h4>Recommended Action</h4>
              <p>{session.recommended_fix}</p>
            </div>
          )}

          {session.next_diagnostic_step && (
            <div className="tm-result-section">
              <h4>Next Diagnostic Step for Engineers</h4>
              <p>{session.next_diagnostic_step}</p>
            </div>
          )}
        </div>
      )
    }

    if (questionData && (session?.status === 'questioning' || !session)) {
      return (
        <div className="tm-question-container">
          <div className="tm-question-header">
            <span className="tm-question-badge">Question {questionData.question_number}/10</span>
          </div>
          <h3 className="tm-question-text">{questionData.question}</h3>
          
          <div className="tm-input-area">
            {renderQuestionInput()}
          </div>

          {error && (
            <div className="tm-error">
              <strong>⚠️ Notice:</strong> {error}
            </div>
          )}

          <div className="tm-action-row">
            <button 
              className="tm-btn-primary" 
              onClick={handleSubmitAnswer}
              disabled={loading}
            >
              {loading ? 'Processing Answer...' : (error ? 'Retry Submit' : 'Submit Answer')}
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="tm-error-container">
        <div className="tm-error">
          <strong>⚠️ Error:</strong> {error || 'An unexpected error occurred during AI analysis.'}
        </div>
        <p style={{ color: '#64748b', fontSize: '0.9rem' }}>
          You can retry the analysis or skip directly to create the issue without AI root-cause analysis.
        </p>
      </div>
    )
  }

  const renderFooter = () => {
    if (session?.status === 'confirmed' || session?.status === 'insufficient_evidence') {
      return (
        <div className="tm-modal-footer">
          <button className="tm-btn-secondary" onClick={handleCancel} disabled={loading || isConfirmingRef.current}>Cancel</button>
          <button
            className="tm-btn-primary"
            onClick={handleConfirmAndCreate}
            disabled={loading || isConfirmingRef.current}
            style={{ pointerEvents: (loading || isConfirmingRef.current) ? 'none' : 'auto' }}
          >
            {loading || isConfirmingRef.current ? 'Creating Issue...' : 'Confirm & Create Issue'}
          </button>
        </div>
      )
    }

    return (
      <div className="tm-modal-footer" style={{ justifyContent: 'space-between' }}>
        <button
          className="tm-btn-text"
          onClick={handleSkip}
          disabled={loading || isSkippingRef.current}
          style={{ pointerEvents: (loading || isSkippingRef.current) ? 'none' : 'auto' }}
        >
          Skip AI Analysis
        </button>
        <button className="tm-btn-secondary" onClick={handleCancel} disabled={loading || isSkippingRef.current}>Cancel</button>
      </div>
    )
  }

  return createPortal(
    <div className="tm-overlay">
      <div className="tm-modal" role="dialog" aria-modal="true">
        <div className="tm-modal-header">
          <div className="tm-header-title">
            <span className="tm-header-icon">🔍</span>
            AI Root-Cause Analysis
          </div>
          <button className="tm-close-btn" onClick={handleCancel}>×</button>
        </div>

        {(session?.status === 'questioning' || questionData) && renderDots()}

        <div className="tm-modal-body">
          {renderContent()}
        </div>

        {renderFooter()}
      </div>

      <style>{`
        .tm-overlay {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(4px);
          display: flex; align-items: center; justify-content: center;
          z-index: 10000;
          animation: tmFadeIn 0.2s ease-out;
        }
        .tm-modal {
          background: #fff;
          width: 90%; max-width: 650px;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          display: flex; flex-direction: column;
          max-height: 90vh;
          overflow: hidden;
          animation: tmSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .tm-modal-header {
          padding: 16px 24px;
          border-bottom: 1px solid #e2e8f0;
          display: flex; justify-content: space-between; align-items: center;
          background: linear-gradient(to right, #f8fafc, #fff);
        }
        .tm-header-title {
          font-weight: 700; color: #0f172a; font-size: 1.1rem;
          display: flex; align-items: center; gap: 8px;
        }
        .tm-header-icon {
          font-size: 1.2rem;
        }
        .tm-close-btn {
          background: none; border: none; font-size: 1.5rem; color: #64748b;
          cursor: pointer; padding: 4px; line-height: 1; border-radius: 4px;
        }
        .tm-close-btn:hover { background: #f1f5f9; color: #0f172a; }
        
        .tm-progress-dots {
          display: flex; gap: 6px; padding: 16px 24px 0; justify-content: center;
        }
        .tm-dot {
          width: 8px; height: 8px; border-radius: 50%;
          background: #e2e8f0; transition: all 0.3s;
        }
        .tm-dot.completed { background: #3b82f6; }
        .tm-dot.active { background: #3b82f6; transform: scale(1.3); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        
        .tm-modal-body {
          padding: 24px;
          overflow-y: auto;
          flex-grow: 1;
        }
        
        /* Question styles */
        .tm-question-header { margin-bottom: 12px; }
        .tm-question-badge {
          background: #eff6ff; color: #2563eb;
          font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
          padding: 4px 8px; border-radius: 4px; letter-spacing: 0.05em;
        }
        .tm-question-text {
          font-size: 1.25rem; font-weight: 600; color: #1e293b;
          margin: 0 0 20px 0; line-height: 1.4;
        }
        .tm-input-area { margin-bottom: 24px; }
        
        .tm-options { display: flex; flex-direction: column; gap: 10px; }
        .tm-option-label {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 12px 16px; border: 1px solid #e2e8f0; border-radius: 8px;
          cursor: pointer; transition: all 0.2s;
        }
        .tm-option-label:hover { border-color: #cbd5e1; background: #f8fafc; }
        .tm-option-label.selected, .tm-option-label:has(input:checked) {
          border-color: #3b82f6; background: #eff6ff;
          box-shadow: 0 0 0 1px #3b82f6;
        }
        .tm-option-label input { margin-top: 4px; }
        .tm-option-text { color: #334155; line-height: 1.5; font-size: 0.95rem; }
        
        .tm-textarea {
          width: 100%; padding: 12px; border: 1px solid #cbd5e1;
          border-radius: 8px; font-family: inherit; font-size: 0.95rem;
          resize: vertical;
        }
        .tm-textarea:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        
        .tm-action-row { display: flex; justify-content: flex-end; }
        
        /* Results Card */
        .tm-result-card {
          padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0;
          background: #f8fafc;
        }
        .tm-result-card.tm-success { border-color: #bbf7d0; background: #f0fdf4; }
        .tm-result-card.tm-warning { border-color: #fef08a; background: #fefce8; }
        .tm-result-icon { font-size: 2.5rem; margin-bottom: 12px; }
        .tm-result-title { font-size: 1.3rem; font-weight: 700; margin: 0 0 4px 0; color: #0f172a; }
        .tm-result-confidence { font-weight: 600; color: #64748b; font-size: 0.9rem; margin-bottom: 20px; }
        .tm-result-card.tm-success .tm-result-confidence { color: #166534; }
        .tm-result-card.tm-warning .tm-result-confidence { color: #854d0e; }
        
        .tm-result-section { margin-bottom: 16px; }
        .tm-result-section h4 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin: 0 0 8px 0; }
        .tm-result-section p { margin: 0; color: #334155; line-height: 1.5; }
        .tm-result-section ul { margin: 0; padding-left: 20px; color: #334155; }
        .tm-result-section ul li { margin-bottom: 4px; line-height: 1.5; }
        
        /* Footer */
        .tm-modal-footer {
          padding: 16px 24px; border-top: 1px solid #e2e8f0;
          display: flex; justify-content: flex-end; gap: 12px;
          background: #f8fafc;
        }
        
        /* Buttons */
        .tm-btn-primary {
          background: #3b82f6; color: white; border: none;
          padding: 10px 20px; border-radius: 8px; font-weight: 600;
          cursor: pointer; transition: all 0.2s; font-size: 0.95rem;
        }
        .tm-btn-primary:hover:not(:disabled) { background: #2563eb; }
        .tm-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
        
        .tm-btn-secondary {
          background: white; color: #475569; border: 1px solid #cbd5e1;
          padding: 10px 20px; border-radius: 8px; font-weight: 600;
          cursor: pointer; transition: all 0.2s; font-size: 0.95rem;
        }
        .tm-btn-secondary:hover:not(:disabled) { background: #f1f5f9; color: #0f172a; }
        .tm-btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
        
        .tm-btn-text {
          background: none; color: #64748b; border: none;
          padding: 10px; font-weight: 600; cursor: pointer;
        }
        .tm-btn-text:hover:not(:disabled) { color: #0f172a; text-decoration: underline; }
        
        .tm-error {
          color: #dc2626; background: #fef2f2; border: 1px solid #fecaca;
          padding: 12px; border-radius: 8px; font-size: 0.9rem;
          margin-bottom: 16px; line-height: 1.4;
        }
        .tm-error-container { padding: 12px 0; }
        
        .tm-loading-state {
          display: flex; flex-direction: column; align-items: center;
          justify-content: center; padding: 40px 0; color: #64748b;
        }
        .tm-spinner {
          width: 32px; height: 32px;
          border: 3px solid #e2e8f0; border-top-color: #3b82f6;
          border-radius: 50%; animation: tmSpin 1s linear infinite;
          margin-bottom: 16px;
        }
        
        @keyframes tmFadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes tmSlideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes tmSpin { to { transform: rotate(360deg); } }
      `}</style>
    </div>,
    document.body
  )
}

