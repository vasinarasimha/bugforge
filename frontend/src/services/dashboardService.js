import apiClient from '../api/client'

export const getDashboardStatistics = () => apiClient.get('/dashboard/statistics')
export const getAdminStats = () => apiClient.get('/admin/stats')
