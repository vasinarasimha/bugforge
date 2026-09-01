import apiClient from '../api/client'

export const getTeams = (params = {}) => apiClient.get('/teams', { params })

export const getTeam = (id) => apiClient.get(`/teams/${id}`)

export const createTeam = (data) => apiClient.post('/teams', data)

export const updateTeam = (id, data) => apiClient.put(`/teams/${id}`, data)

export const deactivateTeam = (id) => apiClient.delete(`/teams/${id}`)

export const getAvailableLeaders = (excludeTeamId = null) =>
  apiClient.get('/teams/meta/available-leaders', {
    params: excludeTeamId ? { exclude_team_id: excludeTeamId } : {},
  })

export const getAvailableMembers = () => apiClient.get('/teams/meta/available-members')

export const getTeamStats = () => apiClient.get('/teams/meta/stats')
