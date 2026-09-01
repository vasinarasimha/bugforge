import apiClient from '../api/client'

/**
 * Analytics Service for BugForge Telemetry & Metrics.
 * Communicates directly with /api/analytics endpoints.
 */

/**
 * Fetch complete analytics overview with database aggregations.
 * @param {number|null} projectId - Optional project ID to filter by
 * @param {number|null} teamId - Optional team ID to filter by
 * @param {number} days - Time window in days (default 30)
 */
export const getAnalyticsOverview = (projectId = null, teamId = null, days = 30) => {
  const params = { days }
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/overview', { params })
}

/**
 * Fetch high-level KPI summaries (total, open, in-progress, resolved, closed, avg resolution time).
 * @param {number|null} projectId - Optional project ID filter
 * @param {number|null} teamId - Optional team ID filter
 */
export const getKPIs = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/kpis', { params })
}

/**
 * Fetch severity distribution (Critical, High, Medium, Low).
 */
export const getSeverityDistribution = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/severity', { params })
}

/**
 * Fetch defect category distribution.
 */
export const getCategoryDistribution = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/category', { params })
}

/**
 * Fetch defect status distribution.
 */
export const getStatusDistribution = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/status', { params })
}

/**
 * Fetch developer workload & task distribution.
 */
export const getDeveloperWorkload = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/developer-workload', { params })
}

/**
 * Fetch defect volume trends over time (created vs resolved).
 */
export const getDefectTrends = (projectId = null, teamId = null, days = 30) => {
  const params = { days }
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
  return apiClient.get('/analytics/trends', { params })
}

/**
 * Fetch resolution time metrics (average, min, max, sample size).
 */
export const getResolutionTimeMetrics = (projectId = null, teamId = null) => {
  const params = {}
  if (projectId) params.project_id = projectId
  if (teamId) params.team_id = teamId
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
