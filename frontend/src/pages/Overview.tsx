import { useEffect, useState } from 'react'
import { getDevicesSummary, getAlerts } from '../services/api'
import { Server, ShieldAlert, Bell, Activity, Package, Network, Clock } from 'lucide-react'
import { Loading, Empty, ErrorBox } from '../components/ui/State'

export default function Overview() {
  const [summary, setSummary] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getDevicesSummary(), getAlerts()])
      .then(([s, a]) => { setSummary(s); setAlerts(a) })
      .catch(() => setError('No se pudo conectar con el backend'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Cargando resumen..." />
  if (error) return <ErrorBox text={error} />

  const ultimo = summary.ultimo_descubrimiento ? new Date(summary.ultimo_descubrimiento).toLocaleString() : 'Sin descubrimientos'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Resumen general</h2>
        <p className="text-slate-400 text-sm">Estado actual de la infraestructura monitorizada (datos persistidos).</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5"><Server className="mb-2 text-accent" /><p className="text-3xl font-bold">{summary.confirmados}</p><p className="text-slate-400">Dispositivos confirmados</p></div>
        <div className="card p-5"><Network className="mb-2 text-accent" /><p className="text-3xl font-bold">{summary.ips_registradas}</p><p className="text-slate-400">Direcciones IP registradas</p></div>
        <div className="card p-5"><Activity className="mb-2 text-green-400" /><p className="text-3xl font-bold">{summary.interfaces_total}</p><p className="text-slate-400">Interfaces de red registradas</p></div>
        <div className="card p-5"><Activity className="mb-2 text-green-400" /><p className="text-3xl font-bold">{summary.activos}</p><p className="text-slate-400">Dispositivos activos</p></div>
        <div className="card p-5"><ShieldAlert className="mb-2 text-slate-400" /><p className="text-3xl font-bold">{summary.inactivos}</p><p className="text-slate-400">Dispositivos inactivos</p></div>
        <div className="card p-5"><Clock className="mb-2 text-yellow-400" /><p className="text-lg font-semibold">{ultimo}</p><p className="text-slate-400">Último descubrimiento</p></div>
        <div className="card p-5"><Bell className="mb-2 text-yellow-400" /><p className="text-3xl font-bold">{alerts.length}</p><p className="text-slate-400">Alertas recientes</p></div>
        <div className="card p-5"><Package className="mb-2 text-accent" /><p className="text-3xl font-bold">{summary.software_asociado}</p><p className="text-slate-400">Aplicaciones inventariadas</p></div>
        <div className="card p-5"><ShieldAlert className="mb-2 text-red-400" /><p className="text-3xl font-bold">{summary.riesgo_alto}</p><p className="text-slate-400">Equipos con riesgo alto</p></div>
      </div>
      {summary.confirmados === 0 && <Empty text="No hay dispositivos descubiertos. Ejecuta un descubrimiento." />}
    </div>
  )
}
