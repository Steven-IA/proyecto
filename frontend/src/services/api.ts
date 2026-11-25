import axios from 'axios'
const api = axios.create({ baseURL: '/api' })
export default api

export async function getDevices(params?: { confirmed_only?: boolean; include_deleted?: boolean }) {
  return (await api.get('/devices/', { params })).data
}
export async function getDevice(id: number) { return (await api.get(`/devices/${id}`)).data }
export async function getDevicesSummary() { return (await api.get('/devices/summary')).data }
export async function getDeviceSoftware(id: number) { return (await api.get(`/devices/${id}/software`)).data }
export async function restoreDevice(id: number) { return (await api.post(`/devices/${id}/restore`)).data }
export async function startDiscovery() { return (await api.post('/discovery/start')).data }
export async function createDiscoveryRequest() { return (await api.post('/discovery/requests')).data }
export async function getDiscoveryRequest(id: string) { return (await api.get(`/discovery/requests/${id}`)).data }
export async function getActiveDiscoveryRequest() { return (await api.get('/discovery/requests/active')).data }
export async function getAgentStatus() { return (await api.get('/agent/status')).data }
export async function getAlerts() { return (await api.get('/alerts/')).data }
export async function getVulns() { return (await api.get('/vulnerabilities/')).data }
export async function getTraining() { return (await api.get('/training/metrics')).data }
export async function assessSecurity(payload: any) { return (await api.post('/security/assess', payload)).data }
export async function analyzeDevice(id: number) { return (await api.post(`/ai/analyze-device/${id}`)).data }
export async function getAnalyses(deviceId?: number) { return (await api.get('/ai/analyses', { params: deviceId ? { device_id: deviceId } : {} })).data }
export async function getAISummary() { return (await api.get('/ai/summary')).data }
export async function generateReport() { return (await api.post('/reports/generate')).data }
export async function downloadReport(filename: string) {
  const res = await api.get(`/reports/download`, { params: { filename }, responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}
export async function getHistory(params?: any) { return (await api.get('/history/', { params })).data }
export async function getSettings() { return (await api.get('/settings/')).data }
export async function updateSetting(key: string, value: string) { return (await api.put(`/settings/${key}`, { value })).data }

export async function deleteDevice(id: number) { return (await api.delete(`/devices/${id}`)).data }
export async function bulkDeleteDevices(ids: number[]) { return (await api.delete('/devices/bulk', { data: { ids } })).data }
export async function deleteAlert(id: number) { return (await api.delete(`/alerts/${id}`)).data }
export async function bulkDeleteAlerts(ids: number[]) { return (await api.delete('/alerts/bulk', { data: { ids } })).data }
export async function deleteVulnerability(id: number) { return (await api.delete(`/vulnerabilities/${id}`)).data }
export async function bulkDeleteVulnerabilities(ids: number[]) { return (await api.delete('/vulnerabilities/bulk', { data: { ids } })).data }
export async function deleteEvent(id: number) { return (await api.delete(`/history/${id}`)).data }
export async function bulkDeleteEvents(ids: number[]) { return (await api.delete('/history/bulk', { data: { ids } })).data }