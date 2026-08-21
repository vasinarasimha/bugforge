import apiClient from '../api/client'

export const getDashboardStatistics = () => apiClient.get('/dashboard/statistics')
export const getAdminStats = () => apiClient.get('/dashboard/admin-stats')
export const getPMStats = () => apiClient.get('/dashboard/pm-stats')
export const getTLStats = () => apiClient.get('/dashboard/tl-stats')
export const getDevStats = () => apiClient.get('/dashboard/dev-stats')
export const getQAStats = () => apiClient.get('/dashboard/qa-stats')
export const getReporterStats = () => apiClient.get('/dashboard/reporter-stats')
