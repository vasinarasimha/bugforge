import apiClient from '../api/client'
export const getProjects = () => apiClient.get('/projects')
export const createProject = (data) => apiClient.post('/projects', data)
export const updateProject = (id, data) => apiClient.put(`/projects/${id}`, data)
export const deleteProject = (id) => apiClient.delete(`/projects/${id}`)
