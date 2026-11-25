import { useEffect, useState } from 'react'
import { getAlerts, deleteAlert, bulkDeleteAlerts } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'
import ConfirmModal from '../components/ui/ConfirmModal'

export default function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [confirm, setConfirm] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const toggle = (id: number) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const load = () => { setLoading(true); getAlerts().then(setAlerts).catch(() => setError('Error al cargar alertas')).finally(() => setLoading(false)) }
  useEffect(load, [])

  const removeOne = (id: number) => setConfirm({ ids: [id] })
  const removeBulk = () => setConfirm({ ids: [...selected] })

  const doDelete = async () => {
    if (!confirm) return
    setBusy(true)
    try {
      if (confirm.ids.length === 1) await deleteAlert(confirm.ids[0])
      else {
        const r = await bulkDeleteAlerts(confirm.ids)
        setMsg(`Eliminadas: ${r.eliminados}, no encontradas: ${r.no_encontrados}`)
      }
      if (confirm.ids.length === 1) setMsg('Alerta eliminada')
      setSelected([])
      load()
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || 'Error al eliminar')
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  if (loading) return <Loading text="Cargando alertas..." />
  if (error) return <ErrorBox text={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Alertas</h2>
        {selected.length > 0 && <button onClick={removeBulk} className="bg-red-600 px-4 py-2 rounded-lg text-sm">Eliminar seleccionadas ({selected.length})</button>}
      </div>
      {msg && <p className="text-slate-300 text-sm">{msg}</p>}
      {alerts.length === 0 ? <Empty text="No hay alertas." /> : (
        <table className="w-full text-sm bg-panel rounded-2xl overflow-hidden border border-slate-800">
          <thead className="bg-slate-800"><tr>
            <th className="p-2"><input type="checkbox" onChange={e => setSelected(e.target.checked ? alerts.map(a => a.id) : [])} /></th>
            <th className="p-2 text-left">Severidad</th><th className="p-2 text-left">Mensaje</th><th className="p-2 text-left">Fecha</th><th className="p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>{alerts.map(a => (
            <tr key={a.id} className="border-t border-slate-700">
              <td className="p-2"><input type="checkbox" checked={selected.includes(a.id)} onChange={() => toggle(a.id)} /></td>
              <td className="p-2">{a.severity}</td><td className="p-2">{a.message}</td><td className="p-2">{new Date(a.created_at).toLocaleString()}</td>
              <td className="p-2"><button onClick={() => removeOne(a.id)} className="text-red-400 text-xs">Eliminar</button></td>
            </tr>
          ))}</tbody>
        </table>
      )}
      {confirm && (
        <ConfirmModal title="Eliminar alertas" message={`Se eliminarán ${confirm.ids.length} alerta(s) permanentemente.`} confirmLabel="Eliminar" loading={busy} onConfirm={doDelete} onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}