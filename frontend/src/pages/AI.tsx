import { useEffect, useState } from 'react'
import { getDevices, getAISummary, getAnalyses, getTraining, analyzeDevice, assessSecurity } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'

export default function AI() {
  const [devices, setDevices] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [analyses, setAnalyses] = useState<any[]>([])
  const [training, setTraining] = useState<any[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [assessment, setAssessment] = useState<any>({ firewall: 'enabled', antivirus: 'enabled', pending_updates: 0, os_age_months: 12, outdated_software: 0, vulnerable_apps: 0, excessive_permissions: false, unnecessary_services: 0, unverified_signatures: 0 })
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => {
    Promise.all([getDevices(), getAISummary(), getAnalyses(), getTraining()])
      .then(([d, s, a, t]) => { setDevices(d); setSummary(s); setAnalyses(a); setTraining(t) })
      .catch(() => setError('Error al cargar datos de IA'))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const run = async () => {
    if (!selected) return
    setMsg('Analizando...')
    setError('')
    try {
      const r = await analyzeDevice(selected)
      setMsg(`Análisis completado: ${r.predicted_class}`)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error al analizar')
    }
  }

  const submitAssessment = async () => {
    if (!selected) return
    try {
      await assessSecurity({ device_id: selected, ...assessment })
      setMsg('Evaluación de seguridad guardada')
      setShowForm(false)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error al guardar evaluación')
    }
  }

  if (loading) return <Loading text="Cargando IA..." />

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Inteligencia Artificial</h2>

      <div className="grid grid-cols-4 gap-3">
        <div className="bg-panel p-3 rounded-xl"><p className="text-2xl font-bold">{summary?.total_analyses ?? 0}</p><p className="text-xs text-slate-400">Análisis realizados</p></div>
        <div className="bg-panel p-3 rounded-xl"><p className="text-2xl font-bold">{summary?.counts?.bajo ?? 0}</p><p className="text-xs text-slate-400">Riesgo bajo</p></div>
        <div className="bg-panel p-3 rounded-xl"><p className="text-2xl font-bold">{summary?.counts?.medio ?? 0}</p><p className="text-xs text-slate-400">Riesgo medio</p></div>
        <div className="bg-panel p-3 rounded-xl"><p className="text-2xl font-bold">{summary?.counts?.alto ?? 0}</p><p className="text-xs text-slate-400">Riesgo alto</p></div>
      </div>

      <div className="bg-panel p-4 rounded-xl">
        <h3 className="font-semibold mb-3">Evaluación de dispositivos</h3>
        <div className="flex gap-2 mb-3">
          <select value={selected ?? ''} onChange={e => setSelected(Number(e.target.value))} className="bg-slate-800 px-3 py-2 rounded flex-1">
            <option value="">Seleccionar dispositivo confirmado</option>
            {devices.filter(d => d.confirmed).map(d => (
              <option key={d.id} value={d.id}>{d.ip} — {d.hostname || 'No disponible'}</option>
            ))}
          </select>
          <button onClick={run} disabled={!selected} className="bg-accent px-4 py-2 rounded disabled:opacity-50">Analizar</button>
        </div>
        {msg && <p className="text-slate-300 text-sm">{msg}</p>}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <p className="text-slate-500 text-xs mt-2">Requiere evaluación de seguridad previa. Si falta información, el análisis devuelve no_data.</p>
        <button onClick={() => setShowForm(!showForm)} className="mt-3 text-sm text-accent">Evaluación manual de seguridad</button>
        {showForm && (
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <label>Firewall
              <select value={assessment.firewall} onChange={e => setAssessment({ ...assessment, firewall: e.target.value })} className="w-full bg-slate-800 px-2 py-1 rounded">
                <option value="enabled">Habilitado</option><option value="disabled">Deshabilitado</option>
              </select>
            </label>
            <label>Antivirus
              <select value={assessment.antivirus} onChange={e => setAssessment({ ...assessment, antivirus: e.target.value })} className="w-full bg-slate-800 px-2 py-1 rounded">
                <option value="enabled">Habilitado</option><option value="disabled">Deshabilitado</option>
              </select>
            </label>
            <label>Actualizaciones pendientes <input type="number" value={assessment.pending_updates} onChange={e => setAssessment({ ...assessment, pending_updates: Number(e.target.value) })} className="w-full bg-slate-800 px-2 py-1 rounded" /></label>
            <label>Antigüedad SO (meses) <input type="number" value={assessment.os_age_months} onChange={e => setAssessment({ ...assessment, os_age_months: Number(e.target.value) })} className="w-full bg-slate-800 px-2 py-1 rounded" /></label>
            <label>Software desactualizado <input type="number" value={assessment.outdated_software} onChange={e => setAssessment({ ...assessment, outdated_software: Number(e.target.value) })} className="w-full bg-slate-800 px-2 py-1 rounded" /></label>
            <label>Servicios innecesarios <input type="number" value={assessment.unnecessary_services} onChange={e => setAssessment({ ...assessment, unnecessary_services: Number(e.target.value) })} className="w-full bg-slate-800 px-2 py-1 rounded" /></label>
            <label>Firmas no verificadas <input type="number" value={assessment.unverified_signatures} onChange={e => setAssessment({ ...assessment, unverified_signatures: Number(e.target.value) })} className="w-full bg-slate-800 px-2 py-1 rounded" /></label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={assessment.excessive_permissions} onChange={e => setAssessment({ ...assessment, excessive_permissions: e.target.checked })} /> Permisos excesivos</label>
            <div className="col-span-2"><button onClick={submitAssessment} className="bg-slate-700 px-4 py-2 rounded">Guardar evaluación</button></div>
          </div>
        )}
      </div>

      <div className="bg-panel p-4 rounded-xl">
        <h3 className="font-semibold mb-3">Historial de análisis</h3>
        {analyses.length === 0 ? <p className="text-slate-400 text-sm">No hay análisis registrados.</p> : (
          <table className="w-full text-sm">
            <thead className="bg-slate-800"><tr><th className="p-2 text-left">Fecha</th><th className="p-2 text-left">Dispositivo</th><th className="p-2 text-left">Clase</th><th className="p-2 text-left">Explicación</th></tr></thead>
            <tbody>{analyses.map(a => (
              <tr key={a.id} className="border-t border-slate-700">
                <td className="p-2">{new Date(a.created_at).toLocaleString()}</td>
                <td className="p-2">{a.device_id}</td>
                <td className="p-2">{a.predicted_class}</td>
                <td className="p-2">{a.explanation}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      <div className="bg-panel p-4 rounded-xl">
        <h3 className="font-semibold mb-3">Estado técnico de modelos</h3>
        {training.map((m, i) => (
          <div key={i} className="mb-3 text-sm">
            <p className="font-semibold">{m.model} — {m.status}</p>
            <p className="text-slate-400">Pesos: {m.weights_available ? 'Sí' : 'No'} | Carga: {m.loaded ? 'Sí' : 'No'}</p>
            {m.metrics && (
              <p className="text-slate-400">Accuracy: {m.metrics.accuracy} (sintético). {m.metrics.limitation}</p>
            )}
          </div>
        ))}
        <div className="mt-3 text-xs text-slate-500">
          <p>Network Transformer: pendiente de integración de telemetría de red. Características requeridas: conn_count, conn_freq, ports, bytes_sent, bytes_recv, duration, activity_var, comm_freq.</p>
        </div>
      </div>
    </div>
  )
}