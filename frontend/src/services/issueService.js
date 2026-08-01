import apiClient from '../api/client'
export const getIssues = () => apiClient.get('/issues')
export const createIssue = (data) => apiClient.post('/issues', data)
export const updateIssue = (id, data) => apiClient.put(`/issues/${id}`, data)
export const deleteIssue = (id) => apiClient.delete(`/issues/${id}`)
