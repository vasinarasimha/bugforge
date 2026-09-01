import apiClient from '../api/client'

export const formatIssue = (data) => apiClient.post('/ai/format-issue', data)

export const getResolutionAssistance = (issueId) => apiClient.post(`/ai/resolution-assistance`, { issue_id: issueId })

export const startTroubleshooting = (data) => apiClient.post('/ai/troubleshooting/start', data)
export const submitTroubleshootingAnswer = (sessionId, data) => apiClient.post(`/ai/troubleshooting/${sessionId}/answer`, data)
export const getTroubleshootingSession = (sessionId) => apiClient.get(`/ai/troubleshooting/${sessionId}`)
export const confirmTroubleshooting = (sessionId, data) => apiClient.post(`/ai/troubleshooting/${sessionId}/confirm`, data)
export const cancelTroubleshooting = (sessionId) => apiClient.post(`/ai/troubleshooting/${sessionId}/cancel`)

export const generateTestCases = (issueId) => apiClient.post('/ai/test-cases', { issue_id: issueId })
export const detectMissingScenarios = (issueId, existingTestCases = null) => apiClient.post('/ai/missing-scenarios', { issue_id: issueId, existing_test_cases: existingTestCases })