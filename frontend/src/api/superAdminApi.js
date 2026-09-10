import apiClient from './client'

export const superAdminApi = {
  getPlatformDashboard: async () => {
    const res = await apiClient.get('/super-admin/dashboard')
    return res.data
  },

  getPlatformAnalytics: async (companyId = null, days = 30) => {
    const params = { days }
    if (companyId) params.company_id = companyId
    const res = await apiClient.get('/super-admin/analytics', { params })
    return res.data
  },

  listCompanies: async (params = {}) => {
    const res = await apiClient.get('/super-admin/companies', { params })
    return res.data
  },

  createCompany: async (data) => {
    const res = await apiClient.post('/super-admin/companies', data)
    return res.data
  },

  getCompanyDetail: async (companyId) => {
    const res = await apiClient.get(`/super-admin/companies/${companyId}`)
    return res.data
  },

  updateCompany: async (companyId, data) => {
    const res = await apiClient.patch(`/super-admin/companies/${companyId}`, data)
    return res.data
  },

  toggleCompanyStatus: async (companyId, isActive) => {
    const res = await apiClient.patch(`/super-admin/companies/${companyId}/status`, null, {
      params: { is_active: isActive },
    })
    return res.data
  },

  getCompanyAuditLogs: async (companyId, limit = 50) => {
    const res = await apiClient.get(`/super-admin/companies/${companyId}/audit-logs`, {
      params: { limit },
    })
    return res.data
  },

  listCustomizationRequests: async (status = null) => {
    const params = status ? { status } : {}
    const res = await apiClient.get('/super-admin/customization-requests', { params })
    return res.data
  },

  reviewCustomizationRequest: async (requestId, data) => {
    const res = await apiClient.patch(`/super-admin/customization-requests/${requestId}`, data)
    return res.data
  },
}

export default superAdminApi
