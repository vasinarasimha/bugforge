import apiClient from '../api/client'

export const getProjects = (search = '', limit = 20, offset = 0) =>
  apiClient.get('/projects', { params: { search, limit, offset } })
export const createProject = (data) => apiClient.post('/projects', data)
export const updateProject = (id, data) => apiClient.put(`/projects/${id}`, data)
export const deleteProject = (id) => apiClient.delete(`/projects/${id}`)
export const getProjectHistory = (id) => apiClient.get(`/projects/${id}/history`)