import apiClient from '../api/client'

/**
 * Analytics Service for BugForge Telemetry & Metrics.
 * Communicates directly with /api/analytics endpoints.
 */

/**
 * Fetch complete analytics overview with database aggregations.
 * @param {number|null} projectId - Optional project ID to filter by
 * @param {number} days - Time window in days (default 30)
 */
export const getAnalyticsOverview = (projectId = null, days = 30) => {
  const params = { days }
  if (projectId) params.project_id = projectId
  return apiClient.get('/analytics/overview', { params })
}

/**
 * Fetch high-level KPI summaries (total, open, in-progress, resolved, closed, avg resolution time).
 * @param {number|null} projectId - Optional project ID filter
 */
export const getKPIs = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/kpis', { params })
}

/**
 * Fetch severity distribution (Critical, High, Medium, Low).
 * @param {number|null} projectId - Optional project ID filter
 */
export const getSeverityDistribution = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/severity', { params })
}

/**
 * Fetch defect category distribution.
 * @param {number|null} projectId - Optional project ID filter
 */
export const getCategoryDistribution = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/category', { params })
}

/**
 * Fetch defect status distribution.
 * @param {number|null} projectId - Optional project ID filter
 */
export const getStatusDistribution = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/status', { params })
}

/**
 * Fetch developer workload & task distribution.
 * @param {number|null} projectId - Optional project ID filter
 */
export const getDeveloperWorkload = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/developer-workload', { params })
}

/**
 * Fetch defect volume trends over time (created vs resolved).
 * @param {number|null} projectId - Optional project ID filter
 * @param {number} days - Number of days (7, 30, 90)
 */
export const getDefectTrends = (projectId = null, days = 30) => {
  const params = { days }
  if (projectId) params.project_id = projectId
  return apiClient.get('/analytics/trends', { params })
}

/**
 * Fetch resolution time metrics (average, min, max, sample size).
 * @param {number|null} projectId - Optional project ID filter
 */
export const getResolutionTimeMetrics = (projectId = null) => {
  const params = projectId ? { project_id: projectId } : {}
  return apiClient.get('/analytics/resolution-time', { params })
}

export default {
  getAnalyticsOverview,
  getKPIs,
  getSeverityDistribution,
  getCategoryDistribution,
  getStatusDistribution,
  getDeveloperWorkload,
  getDefectTrends,
  getResolutionTimeMetrics,
}
