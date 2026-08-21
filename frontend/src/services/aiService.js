import apiClient from '../api/client'

export const formatIssue = (data) => apiClient.post('/ai/format-issue', data)

export const getResolutionAssistance = (issueId) => apiClient.post(`/ai/resolution-assistance`, { issue_id: issueId })