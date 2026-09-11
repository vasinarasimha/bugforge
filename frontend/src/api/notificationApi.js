import apiClient from './client'

export const notificationApi = {
  getMyNotifications: async (unreadOnly = false, limit = 50, offset = 0) => {
    const res = await apiClient.get('/notifications', {
      params: { unread_only: unreadOnly, limit, offset },
    })
    return res.data
  },

  getUnreadCount: async () => {
    const res = await apiClient.get('/notifications/unread-count')
    return res.data
  },

  markAsRead: async (notificationId) => {
    const res = await apiClient.patch(`/notifications/${notificationId}/read`)
    return res.data
  },

  markAllAsRead: async () => {
    const res = await apiClient.post('/notifications/mark-all-read')
    return res.data
  },

  clearReadNotifications: async (olderThanDays = 0) => {
    const res = await apiClient.delete('/notifications/read', {
      params: { older_than_days: olderThanDays },
    })
    return res.data
  },
}
