import { useEffect, useState } from 'react'
import { getHistory, deleteEvent, bulkDeleteEvents } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'
import ConfirmModal from '../components/ui/ConfirmModal'

export default function HistoryPage() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [confirm, setConfirm] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = () => {
    setLoading(true)
    getHistory({ event_type: type || undefined, q: q || undefined })
      .then(setEvents).catch(() => setError('Error al cargar historial')).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const toggle = (id: number) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const removeOne = (id: number) => setConfirm({ ids: [id] })
  const removeBulk = () => setConfirm({ ids: [...selected] })

  const doDelete = async () => {
    if (!confirm) return
    setBusy(true)
    try {
      if (confirm.ids.length === 1) await deleteEvent(confirm.ids[0])
      else {
        const r = await bulkDeleteEvents(confirm.ids)
        setMsg(`Eliminados: ${r.eliminados}, no encontrados: ${r.no_encontrados}`)
      }
      if (confirm.ids.length === 1) setMsg('Evento eliminado')
      setSelected([])
      load()
    } catch (e: any) { setMsg(e?.response?.data?.detail || 'Error al eliminar') }
    finally { setBusy(false); setConfirm(null) }
  }

  if (loading) return <Loading text="Cargando historial..." />
  if (error) return <ErrorBox text={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Historial</h2>
        {selected.length > 0 && <button onClick={removeBulk} className="bg-red-600 px-4 py-2 rounded-lg text-sm">Eliminar seleccionados ({selected.length})</button>}
      </div>
      <div className="flex gap-2 mb-4">
        <select value={type} onChange={e => setType(e.target.value)} className="bg-panel px-3 py-2 rounded">
          <option value="">Todos los tipos</option>
          <option value="discovery">Descubrimiento</option>
          <option value="availability">Disponibilidad</option>
          <option value="security">Seguridad</option>
          <option value="vulnerability">Vulnerabilidades</option>
        </select>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar..." className="bg-panel px-3 py-2 rounded flex-1" />
        <button onClick={load} className="bg-accent px-4 py-2 rounded">Filtrar</button>
      </div>
      {msg && <p className="text-slate-300 text-sm">{msg}</p>}
      {events.length === 0 ? <Empty text="No hay eventos registrados." /> : (
        <table className="w-full text-sm bg-panel rounded-2xl overflow-hidden border border-slate-800">
          <thead className="bg-slate-800"><tr>
            <th className="p-2"><input type="checkbox" onChange={e => setSelected(e.target.checked ? events.map(ev => ev.id) : [])} /></th>
            <th className="p-2 text-left">Fecha</th><th className="p-2 text-left">Tipo</th><th className="p-2 text-left">Dispositivo</th><th className="p-2 text-left">Mensaje</th><th className="p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>{events.map(e => (
            <tr key={e.id} className="border-t border-slate-700">
              <td className="p-2"><input type="checkbox" checked={selected.includes(e.id)} onChange={() => toggle(e.id)} /></td>
              <td className="p-2">{new Date(e.created_at).toLocaleString()}</td>
              <td className="p-2">{e.event_type}</td>
              <td className="p-2">{e.device_id ?? 'N/A'}</td>
              <td className="p-2">{e.message}</td>
              <td className="p-2"><button onClick={() => removeOne(e.id)} className="text-red-400 text-xs">Eliminar</button></td>
            </tr>
          ))}</tbody>
        </table>
      )}
      {confirm && (
        <ConfirmModal title="Eliminar eventos" message={`Se eliminarán ${confirm.ids.length} evento(s) permanentemente.`} confirmLabel="Eliminar" loading={busy} onConfirm={doDelete} onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}