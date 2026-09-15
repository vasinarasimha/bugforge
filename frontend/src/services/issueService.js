import apiClient from '../api/client'

export const extractErrorMessage = (err, fallback = 'Operation failed.') => {
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
        return detail.map(d => d.msg || JSON.stringify(d)).join('; ')
    }
    if (detail && typeof detail === 'object') {
        return detail.message || detail.msg || JSON.stringify(detail)
    }
    return err?.message || fallback
}

export const getIssues = (params = {}) => apiClient.get('/issues', { params })
export const getStatuses = () => apiClient.get('/issues/statuses')
export const getPriorities = () => apiClient.get('/issues/priorities')
export const getSeverities = () => apiClient.get('/issues/severities')
export const getCategories = () => apiClient.get('/issues/categories')
export const getModules = () => apiClient.get('/issues/modules')
export const createIssue = (data) => apiClient.post('/issues', data)
export const updateIssue = (id, data) => apiClient.put(`/issues/${id}`, data)
export const deleteIssue = (id) => apiClient.delete(`/issues/${id}`)
export const getIssueHistory = (id) => apiClient.get(`/issues/${id}/history`)
export const getIssue = (id) => apiClient.get(`/issues/${id}`)
export const getIssueComments = (id) => apiClient.get(`/issues/${id}/comments`)
export const addIssueComment = (id, data) => apiClient.post(`/issues/${id}/comments`, data)
export const uploadFile = (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/uploads', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

export const getIssueAttachments = (id) => apiClient.get(`/issues/${id}/attachments`);

export const addIssueAttachment = (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/issues/${id}/attachments`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
};

export const deleteIssueAttachment = (id, attachmentId) => apiClient.delete(`/issues/${id}/attachments/${attachmentId}`)
export const updateIssueStatus = (id, data) => apiClient.patch(`/issues/${id}/status`, data)
export const updateIssueAssignee = (id, data) => apiClient.patch(`/issues/${id}/assign`, data)
export const updateIssueQaAssignee = (id, data) => apiClient.patch(`/issues/${id}/assign-qa`, data)

// ── Semantic Search & Similar Issues ──


/** Search issues using a natural-language query */
export const semanticSearch = (query, projectId = null, limit = null) =>
    apiClient.post('/issues/semantic-search', { query, project_id: projectId, limit })

/** Find similar issues for an existing issue */
export const getSimilarIssues = (issueId, projectId = null) =>
    apiClient.get(`/issues/${issueId}/similar`, { params: { project_id: projectId } })

/** Legacy search by title+description (backward compatible) */
export const searchIssues = (title, description, projectId = null, excludeIssueId = null) =>
    apiClient.post('/issues/search', { title, description, project_id: projectId, exclude_issue_id: excludeIssueId })

export const submitFeatureRequest = (data) => apiClient.post('/issues/feature-requests', data)
export const assignIssueTeam = (issueId, teamData) => {
    const team_id = typeof teamData === 'object' && teamData !== null && 'team_id' in teamData
        ? Number(teamData.team_id)
        : Number(teamData)
    return apiClient.patch(`/issues/${issueId}/assign-team`, { team_id })
}
export const qaVerifyIssue = (issueId, qaState, notes = null) => apiClient.patch(`/issues/${issueId}/qa-verify`, { qa_state: qaState, notes })

/** Unified hybrid search combining keyword and vector semantic search */
export const hybridSearch = (query = '', projectId = null, statusId = null, limit = 50) =>
    apiClient.post('/issues/hybrid-search', { query, project_id: projectId ? Number(projectId) : null, status_id: statusId ? Number(statusId) : null, limit })
