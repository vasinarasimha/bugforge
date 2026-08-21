import apiClient from '../api/client'
export const getIssues = () => apiClient.get('/issues')
export const getStatuses = () => apiClient.get('/issues/statuses')
export const getPriorities = () => apiClient.get('/issues/priorities')
export const getSeverities = () => apiClient.get('/issues/severities')
export const getCategories = () => apiClient.get('/issues/categories')
export const getModules = () => apiClient.get('/issues/modules')
export const searchIssues = (q) => apiClient.get(`/issues/search?q=${encodeURIComponent(q)}`)
export const createIssue = (data) => apiClient.post('/issues', data)
export const updateIssue = (id, data) => apiClient.put(`/issues/${id}`, data)
export const deleteIssue = (id) => apiClient.delete(`/issues/${id}`)
export const getIssueHistory = (id) => apiClient.get(`/issues/${id}/history`)
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

