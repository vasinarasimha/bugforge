import React, { useState } from 'react'
import { generateTestCases, detectMissingScenarios } from '../../services/aiService'

export default function AITestIntelligence({ issueId, onClose }) {
  const [activeTab, setActiveTab] = useState('testCases') // 'testCases' | 'missingScenarios'

  // Test Cases State
  const [testCasesData, setTestCasesData] = useState(null)
  const [testCasesLoading, setTestCasesLoading] = useState(false)
  const [testCasesError, setTestCasesError] = useState('')
  const [expandedCases, setExpandedCases] = useState({})

  // Missing Scenarios State
  const [missingData, setMissingData] = useState(null)
  const [missingLoading, setMissingLoading] = useState(false)
  const [missingError, setMissingError] = useState('')

  // Copy status
  const [copiedId, setCopiedId] = useState(null)

  const handleFetchTestCases = async () => {
    if (!issueId) return
    setTestCasesLoading(true)
    setTestCasesError('')
    try {
      const { data } = await generateTestCases(issueId)
      setTestCasesData(data)
      // Expand all by default
      const initialExpanded = {}
      data.test_cases?.forEach(tc => { initialExpanded[tc.test_case_id] = true })
      setExpandedCases(initialExpanded)
    } catch (err) {
      console.error('Failed to generate test cases:', err)
      setTestCasesError(err.response?.data?.detail || 'Failed to generate test cases. Please try again.')
    } finally {
      setTestCasesLoading(false)
    }
  }

  const handleFetchMissingScenarios = async () => {
    if (!issueId) return
    setMissingLoading(true)
    setMissingError('')
    try {
      const existingCases = testCasesData?.test_cases || null
      const { data } = await detectMissingScenarios(issueId, existingCases)
      setMissingData(data)
    } catch (err) {
      console.error('Failed to detect missing scenarios:', err)
      setMissingError(err.response?.data?.detail || 'Failed to analyze edge cases. Please try again.')
    } finally {
      setMissingLoading(false)
    }
  }

  const toggleExpand = (id) => {
    setExpandedCases(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleCopyTestCase = (tc) => {
    const text = [
      `[${tc.test_case_id}] ${tc.scenario}`,
      `Type: ${tc.test_type} | Priority: ${tc.priority}`,
      `Preconditions: ${tc.preconditions}`,
      `Steps:\n${tc.steps.map((s, i) => `  ${i + 1}. ${s.replace(/^\d+\.\s*/, '')}`).join('\n')}`,
      tc.test_data ? `Test Data: ${tc.test_data}` : '',
      `Expected Result: ${tc.expected_result}`
    ].filter(Boolean).join('\n')

    navigator.clipboard.writeText(text)
    setCopiedId(tc.test_case_id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getPriorityBadgeStyle = (priority) => {
    const p = String(priority).toLowerCase()
    if (p.includes('crit') || p.includes('high')) {
      return { background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', border: '1px solid rgba(239, 68, 68, 0.2)' }
    }
    if (p.includes('med')) {
      return { background: 'rgba(245, 158, 11, 0.1)', color: '#d97706', border: '1px solid rgba(245, 158, 11, 0.2)' }
    }
    return { background: 'rgba(16, 185, 129, 0.1)', color: '#059669', border: '1px solid rgba(16, 185, 129, 0.2)' }
  }

  const getRiskBadgeStyle = (risk) => {
    const r = String(risk).toLowerCase()
    if (r === 'high') {
      return { background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca' }
    }
    if (r === 'medium') {
      return { background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }
    }
    return { background: '#dbeafe', color: '#1e40af', border: '1px solid #bfdbfe' }
  }

  return (
    <div className="qa-intel-card">
      <style>{`
        .qa-intel-card {
          background: #fff;
          border: 1px solid rgba(15, 23, 42, 0.08);
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
          margin-bottom: 24px;
          display: flex;
          flex-direction: column;
          animation: qaFadeIn 0.3s ease-out;
        }
        .qa-intel-header {
          padding: 16px 20px;
          background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 50%, #f8fafc 100%);
          border-bottom: 1px solid rgba(15, 23, 42, 0.07);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .qa-intel-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 700;
          font-size: 0.95rem;
          color: #065f46;
          letter-spacing: 0.02em;
        }
        .qa-intel-close-btn {
          background: none;
          border: none;
          font-size: 1.25rem;
          color: #64748b;
          cursor: pointer;
          line-height: 1;
          padding: 4px;
          border-radius: 6px;
        }
        .qa-intel-close-btn:hover { background: rgba(0, 0, 0, 0.05); color: #0f172a; }

        .qa-intel-nav {
          display: flex;
          border-bottom: 1px solid #e2e8f0;
          background: #fafbfc;
          padding: 0 16px;
        }
        .qa-tab-btn {
          padding: 12px 18px;
          font-size: 0.85rem;
          font-weight: 600;
          color: #64748b;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .qa-tab-btn:hover { color: #0f172a; }
        .qa-tab-btn.active {
          color: #059669;
          border-bottom-color: #059669;
          background: #fff;
        }

        .qa-intel-body {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          max-height: 750px;
          overflow-y: auto;
          scrollbar-width: thin;
        }

        .qa-btn-action-primary {
          background: linear-gradient(135deg, #059669, #0d9488);
          color: #fff;
          border: none;
          padding: 10px 18px;
          border-radius: 8px;
          font-size: 0.88rem;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
          transition: all 0.2s;
        }
        .qa-btn-action-primary:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35);
        }
        .qa-btn-action-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        .qa-btn-action-secondary {
          background: #fff;
          color: #065f46;
          border: 1.5px solid #a7f3d0;
          padding: 8px 14px;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s;
        }
        .qa-btn-action-secondary:hover:not(:disabled) { background: #f0fdf4; border-color: #059669; }
        .qa-btn-action-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

        .qa-empty-state {
          text-align: center;
          padding: 32px 16px;
          color: #64748b;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }
        .qa-empty-icon { font-size: 2.2rem; }
        .qa-empty-title { font-size: 1rem; font-weight: 700; color: #1e293b; margin: 0; }
        .qa-empty-desc { font-size: 0.85rem; color: #64748b; max-width: 380px; margin: 0; line-height: 1.5; }

        /* Summary Chips */
        .qa-summary-box {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 14px 16px;
        }
        .qa-summary-overview {
          font-size: 0.86rem;
          color: #334155;
          margin-bottom: 10px;
          line-height: 1.5;
        }
        .qa-chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .qa-chip {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 700;
          background: #e2e8f0;
          color: #334155;
        }
        .qa-chip.total { background: #059669; color: #fff; }

        /* Test Case Card */
        .qa-tc-card {
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          background: #fff;
          transition: all 0.2s;
          overflow: hidden;
        }
        .qa-tc-card:hover { border-color: #cbd5e1; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
        .qa-tc-header {
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          cursor: pointer;
          background: #fafbfc;
          user-select: none;
          transition: background 0.15s;
        }
        .qa-tc-header:hover { background: #f8fafc; }
        .qa-tc-top-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .qa-tc-scenario-row {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .qa-tc-id {
          font-size: 0.75rem;
          font-weight: 800;
          color: #059669;
          background: #ecfdf5;
          padding: 2px 6px;
          border-radius: 4px;
          border: 1px solid #a7f3d0;
          flex-shrink: 0;
        }
        .qa-tc-scenario {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1e293b;
          line-height: 1.45;
        }
        .qa-badge {
          font-size: 0.7rem;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 12px;
          text-transform: capitalize;
        }
        .qa-badge.type {
          background: #f1f5f9;
          color: #475569;
          border: 1px solid #cbd5e1;
        }

        .qa-tc-details {
          padding: 14px 16px;
          border-top: 1px solid #f1f5f9;
          font-size: 0.85rem;
          color: #334155;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .qa-field-row { display: flex; flex-direction: column; gap: 3px; }
        .qa-field-label {
          font-size: 0.72rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #64748b;
        }
        .qa-steps-list {
          margin: 0;
          padding-left: 18px;
          line-height: 1.6;
        }
        .qa-steps-list li { margin-bottom: 2px; }

        .qa-copy-btn {
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          color: #475569;
          font-size: 0.75rem;
          font-weight: 600;
          padding: 4px 8px;
          border-radius: 6px;
          cursor: pointer;
          align-self: flex-start;
          transition: all 0.2s;
        }
        .qa-copy-btn:hover { background: #f1f5f9; color: #0f172a; }

        /* Missing Scenarios */
        .qa-missing-card {
          border-radius: 10px;
          border: 1px solid #fef08a;
          background: #fefce8;
          padding: 14px 16px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .qa-missing-top-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .qa-missing-title {
          font-size: 0.92rem;
          font-weight: 700;
          color: #854d0e;
          display: flex;
          align-items: flex-start;
          gap: 8px;
          line-height: 1.45;
        }

        .qa-disclaimer {
          font-size: 0.78rem;
          color: #64748b;
          font-style: italic;
          background: #f8fafc;
          border: 1px dashed #cbd5e1;
          padding: 8px 12px;
          border-radius: 8px;
          line-height: 1.4;
        }

        .qa-covered-box {
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          border-radius: 10px;
          padding: 12px 14px;
        }
        .qa-covered-title {
          font-size: 0.8rem;
          font-weight: 700;
          color: #166534;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          margin-bottom: 6px;
        }
        .qa-covered-list {
          margin: 0;
          padding-left: 18px;
          font-size: 0.82rem;
          color: #15803d;
        }

        .qa-error-box {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #dc2626;
          padding: 12px 16px;
          border-radius: 8px;
          font-size: 0.88rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .qa-loading-box {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 36px 16px;
          gap: 12px;
          color: #065f46;
        }
        .qa-spinner {
          width: 28px;
          height: 28px;
          border: 3px solid #d1fae5;
          border-top-color: #059669;
          border-radius: 50%;
          animation: qaSpin 1s linear infinite;
        }

        @keyframes qaFadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes qaSpin { to { transform: rotate(360deg); } }
      `}</style>

      {/* Header */}
      <div className="qa-intel-header">
        <div className="qa-intel-title">
          <span>🧪</span>
          <span>AI Test Intelligence</span>
        </div>
        {onClose && (
          <button type="button" className="qa-intel-close-btn" onClick={onClose} title="Close AI Test Intelligence">
            ×
          </button>
        )}
      </div>

      {/* Nav Tabs */}
      <div className="qa-intel-nav">
        <button 
          type="button" 
          className={`qa-tab-btn ${activeTab === 'testCases' ? 'active' : ''}`}
          onClick={() => setActiveTab('testCases')}
        >
          <span>📋</span> Test Cases {testCasesData?.test_cases?.length ? `(${testCasesData.test_cases.length})` : ''}
        </button>
        <button 
          type="button" 
          className={`qa-tab-btn ${activeTab === 'missingScenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('missingScenarios')}
        >
          <span>🔍</span> Missing Scenarios {missingData?.missing_scenarios?.length ? `(${missingData.missing_scenarios.length})` : ''}
        </button>
      </div>

      {/* Content */}
      <div className="qa-intel-body">

        {/* ── TAB 1: TEST CASES ── */}
        {activeTab === 'testCases' && (
          <>
            {testCasesLoading ? (
              <div className="qa-loading-box">
                <div className="qa-spinner" />
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Analyzing defect and generating QA test cases…</span>
              </div>
            ) : testCasesError ? (
              <div className="qa-error-box">
                <span>{testCasesError}</span>
                <button type="button" className="qa-btn-action-secondary" onClick={handleFetchTestCases}>Retry</button>
              </div>
            ) : !testCasesData ? (
              <div className="qa-empty-state">
                <div className="qa-empty-icon">📋</div>
                <h4 className="qa-empty-title">Generate QA Test Suite</h4>
                <p className="qa-empty-desc">
                  AI will analyze this defect's reproduction steps, behaviors, priority, and root cause to synthesize functional, negative, boundary, and regression test cases.
                </p>
                <button 
                  type="button" 
                  className="qa-btn-action-primary" 
                  onClick={handleFetchTestCases}
                >
                  <span>✨</span> Generate Test Cases
                </button>
              </div>
            ) : (
              <>
                {/* Actions & Summary */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button 
                    type="button" 
                    className="qa-btn-action-secondary" 
                    onClick={handleFetchTestCases}
                    disabled={testCasesLoading}
                  >
                    <span>🔄</span> Regenerate
                  </button>
                  {!missingData && (
                    <button 
                      type="button" 
                      className="qa-btn-action-secondary" 
                      onClick={() => { setActiveTab('missingScenarios'); handleFetchMissingScenarios(); }}
                    >
                      <span>🔍</span> Detect Missing Scenarios
                    </button>
                  )}
                </div>

                {/* Summary Breakdown */}
                {testCasesData.summary && (
                  <div className="qa-summary-box">
                    <div className="qa-summary-overview">{testCasesData.summary.overview}</div>
                    <div className="qa-chip-row">
                      <span className="qa-chip total">Total: {testCasesData.summary.total_count}</span>
                      {Object.entries(testCasesData.summary.by_type || {}).map(([type, count]) => (
                        <span key={type} className="qa-chip">
                          {type}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Test Cases List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {testCasesData.test_cases?.map(tc => {
                    const isExpanded = !!expandedCases[tc.test_case_id]
                    return (
                      <div key={tc.test_case_id} className="qa-tc-card">
                        <div className="qa-tc-header" onClick={() => toggleExpand(tc.test_case_id)}>
                          {/* Row 1: Badges & Expand state */}
                          <div className="qa-tc-top-row">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span className="qa-tc-id">{tc.test_case_id}</span>
                              <span className="qa-badge type">{tc.test_type}</span>
                              <span className="qa-badge" style={getPriorityBadgeStyle(tc.priority)}>
                                {tc.priority} Priority
                              </span>
                            </div>
                            <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                              {isExpanded ? '▲ Collapse' : '▼ Expand'}
                            </span>
                          </div>

                          {/* Row 2: Scenario Title (Full Width) */}
                          <div className="qa-tc-scenario-row">
                            <span className="qa-tc-scenario">{tc.scenario}</span>
                          </div>
                        </div>

                        {isExpanded && (
                          <div className="qa-tc-details">
                            {tc.preconditions && (
                              <div className="qa-field-row">
                                <span className="qa-field-label">Preconditions</span>
                                <div>{tc.preconditions}</div>
                              </div>
                            )}

                            {tc.steps && tc.steps.length > 0 && (
                              <div className="qa-field-row">
                                <span className="qa-field-label">Test Steps</span>
                                <ol className="qa-steps-list">
                                  {tc.steps.map((step, idx) => (
                                    <li key={idx}>{step.replace(/^\d+\.\s*/, '')}</li>
                                  ))}
                                </ol>
                              </div>
                            )}

                            {tc.test_data && tc.test_data !== 'N/A' && (
                              <div className="qa-field-row">
                                <span className="qa-field-label">Test Data</span>
                                <code style={{ fontSize: '0.82rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                                  {tc.test_data}
                                </code>
                              </div>
                            )}

                            <div className="qa-field-row">
                              <span className="qa-field-label">Expected Result</span>
                              <div style={{ color: '#065f46', fontWeight: 500 }}>{tc.expected_result}</div>
                            </div>

                            <button 
                              type="button" 
                              className="qa-copy-btn"
                              onClick={(e) => { e.stopPropagation(); handleCopyTestCase(tc); }}
                            >
                              {copiedId === tc.test_case_id ? '✓ Copied!' : '📋 Copy Test Case'}
                            </button>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </>
        )}

        {/* ── TAB 2: MISSING SCENARIOS ── */}
        {activeTab === 'missingScenarios' && (
          <>
            {missingLoading ? (
              <div className="qa-loading-box">
                <div className="qa-spinner" />
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Scanning for overlooked edge cases & coverage gaps…</span>
              </div>
            ) : missingError ? (
              <div className="qa-error-box">
                <span>{missingError}</span>
                <button type="button" className="qa-btn-action-secondary" onClick={handleFetchMissingScenarios}>Retry</button>
              </div>
            ) : !missingData ? (
              <div className="qa-empty-state">
                <div className="qa-empty-icon">🔍</div>
                <h4 className="qa-empty-title">Edge-Case & Gap Detection</h4>
                <p className="qa-empty-desc">
                  Identify potentially overlooked test conditions such as network timeouts, session expiration, concurrency, extreme boundary values, and permission edge cases.
                </p>
                <button 
                  type="button" 
                  className="qa-btn-action-primary" 
                  onClick={handleFetchMissingScenarios}
                >
                  <span>🔍</span> Find Missing Scenarios
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button 
                    type="button" 
                    className="qa-btn-action-secondary" 
                    onClick={handleFetchMissingScenarios}
                    disabled={missingLoading}
                  >
                    <span>🔄</span> Re-scan Edge Cases
                  </button>
                  <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>
                    {missingData.missing_scenarios?.length || 0} gaps detected
                  </span>
                </div>

                {/* Already Covered Summary */}
                {missingData.already_covered_summary && missingData.already_covered_summary.length > 0 && (
                  <div className="qa-covered-box">
                    <div className="qa-covered-title">✓ Baseline Scenarios Already Covered</div>
                    <ul className="qa-covered-list">
                      {missingData.already_covered_summary.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Missing Scenarios Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {missingData.missing_scenarios?.map((ms, idx) => (
                    <div key={idx} className="qa-missing-card">
                      {/* Row 1: Badges & Scenario Counter */}
                      <div className="qa-missing-top-meta">
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <span className="qa-badge" style={getRiskBadgeStyle(ms.risk)}>
                            {ms.risk} Risk
                          </span>
                          <span className="qa-badge" style={getPriorityBadgeStyle(ms.priority)}>
                            {ms.priority} Priority
                          </span>
                        </div>
                        <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>
                          Scenario #{idx + 1}
                        </span>
                      </div>

                      {/* Row 2: Scenario Title (Full Width) */}
                      <div className="qa-missing-title">
                        <span style={{ fontSize: '1rem', flexShrink: 0, marginTop: '1px' }}>⚠️</span>
                        <span>{ms.scenario}</span>
                      </div>

                      {/* Row 3: Why it matters */}
                      <div style={{ fontSize: '0.84rem', color: '#451a03', lineHeight: 1.5 }}>
                        <strong>Why it matters:</strong> {ms.why_it_matters}
                      </div>

                      {/* Row 4: Suggested Test */}
                      <div style={{ fontSize: '0.84rem', color: '#1e293b', background: '#fff', padding: '10px 12px', borderRadius: '8px', border: '1px solid #fef08a', lineHeight: 1.5 }}>
                        <strong style={{ color: '#065f46' }}>Suggested Test:</strong> {ms.suggested_test}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Disclaimer */}
                {missingData.disclaimer && (
                  <div className="qa-disclaimer">
                    ℹ️ {missingData.disclaimer}
                  </div>
                )}
              </>
            )}
          </>
        )}

      </div>
    </div>
  )
}
