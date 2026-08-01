import apiClient from '../api/client'

export const formatIssue = (data) => apiClient.post('/ai/format-issue', data)
export const summarizeTimeline = (data) => apiClient.post('/ai/summarize-timeline', data)
