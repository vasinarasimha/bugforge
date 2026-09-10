import apiClient from './client'

export const companyApi = {
  getProfile: async () => {
    const res = await apiClient.get('/company/profile')
    return res.data
  },

  updateProfile: async (data) => {
    const res = await apiClient.patch('/company/profile', data)
    return res.data
  },

  getSettings: async () => {
    const res = await apiClient.get('/company/settings')
    return res.data
  },

  updateSettings: async (settings) => {
    const res = await apiClient.put('/company/settings', { settings })
    return res.data
  },

  listStatuses: async () => {
    const res = await apiClient.get('/company/statuses')
    return res.data
  },

  createStatus: async (data) => {
    const res = await apiClient.post('/company/statuses', data)
    return res.data
  },

  updateStatus: async (statusId, data) => {
    const res = await apiClient.patch(`/company/statuses/${statusId}`, data)
    return res.data
  },

  deleteOrDeactivateStatus: async (statusId) => {
    const res = await apiClient.delete(`/company/statuses/${statusId}`)
    return res.data
  },

  listRequests: async () => {
    const res = await apiClient.get('/company/customization-requests')
    return res.data
  },

  submitRequest: async (data) => {
    const res = await apiClient.post('/company/customization-requests', data)
    return res.data
  },

  listAuditLogs: async (limit = 50) => {
    const res = await apiClient.get('/company/audit-logs', { params: { limit } })
    return res.data
  },
}

export default companyApi
