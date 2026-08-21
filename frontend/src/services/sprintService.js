import apiClient from '../api/client'

export const getSprints = (project_id = null, search = '', limit = 100, offset = 0) => {
  return apiClient.get('/sprints', { params: { project_id, search, limit, offset } })
}

export const getSprintStatuses = () => apiClient.get('/sprints/statuses')
export const createSprint = (data) => apiClient.post('/sprints', data)
export const updateSprint = (id, data) => apiClient.put(`/sprints/${id}`, data)
export const deleteSprint = (id) => apiClient.delete(`/sprints/${id}`)
export const assignIssueToSprint = (sprint_id, issue_id) => apiClient.put(`/sprints/${sprint_id}/issues/${issue_id}`)
export const removeIssueFromSprint = (sprint_id, issue_id) => apiClient.delete(`/sprints/${sprint_id}/issues/${issue_id}`)
