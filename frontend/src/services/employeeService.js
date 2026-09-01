import apiClient from '../api/client'

export const getEmployees = (params = {}) =>
  apiClient.get('/admin/users', { params })

export const getEmployeeById = (id) =>
  apiClient.get(`/admin/users/${id}`)

export const createEmployee = (employeeData) =>
  apiClient.post('/admin/users', employeeData)

export const updateEmployee = (id, updateData) =>
  apiClient.patch(`/admin/users/${id}`, updateData)

export const deactivateEmployee = (id) =>
  apiClient.delete(`/admin/users/${id}`)

export const getRoles = () =>
  apiClient.get('/admin/roles')
