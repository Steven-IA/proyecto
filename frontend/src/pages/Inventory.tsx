import { useEffect, useState, useRef, Fragment } from 'react'
import { getDevices, getDevice, createDiscoveryRequest, getDiscoveryRequest, getAgentStatus, deleteDevice, bulkDeleteDevices, restoreDevice, getDeviceSoftware } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'
import ConfirmModal from '../components/ui/ConfirmModal'

const NA = 'No disponible'
const fmt = (v: any) => (v === null || v === undefined || v === '' ? NA : String(v))
const fmtDate = (v: any) => (v ? new Date(v).toLocaleString() : NA)

export default function Inventory() {
  const [devices, setDevices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [requestId, setRequestId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [confirm, setConfirm] = useState<any>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [agentStatus, setAgentStatus] = useState<any>(null)
  const [showArchived, setShowArchived] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [detail, setDetail] = useState<any>(null)
  const [detailSoftware, setDetailSoftware] = useState<any[]>([])
  const [loadingId, setLoadingId] = useState<number | null>(null)
  const timer = useRef<any>(null)
  const agentTimer = useRef<any>(null)

  const load = (archived = showArchived) => {
    setLoading(true)
    getDevices({ include_deleted: archived })
      .then(setDevices)
      .catch(() => setError('Error al cargar inventario'))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load(showArchived) }, [showArchived])

  const loadAgent = () => { getAgentStatus().then(setAgentStatus).catch(() => setAgentStatus({ connected: false })) }
  useEffect(() => { loadAgent(); agentTimer.current = setInterval(loadAgent, 15000); return () => { if (agentTimer.current) clearInterval(agentTimer.current) } }, [])

  const poll = (id: string) => {
    timer.current = setInterval(async () => {
      try {
        const r = await getDiscoveryRequest(id)
        setStatus(r.status)
        if (r.status === 'completed') {
          clearInterval(timer.current); setBusy(false)
          setMsg(`Descubiertos: ${r.discovered_count}, recibidos: ${r.received_count ?? 0}, confirmados: ${r.confirmed_count ?? 0}, actualizados: ${r.updated_count ?? 0}, archivados sin reactivar: ${r.archived_count ?? 0}, rechazados: ${r.rejected_count}`)
          load()
        }
        else if (r.status === 'error') { clearInterval(timer.current); setBusy(false); setMsg(`Error: ${r.error_message || 'descubrimiento fallido'}`) }
      } catch { clearInterval(timer.current); setBusy(false); setMsg('Error consultando estado') }
    }, 2000)
  }
  useEffect(() => () => { if (timer.current) clearInterval(timer.current) }, [])

  const discover = async () => {
    if (busy) return
    setBusy(true); setMsg('Solicitando descubrimiento...'); setStatus('pendiente')
    try {
      const r = await createDiscoveryRequest()
      setRequestId(r.id); setStatus(r.status)
      setMsg(r.created ? 'Solicitud creada. Esperando al agente Windows...' : 'Ya existe una solicitud activa.')
      poll(r.id)
    } catch { setBusy(false); setMsg('Error al crear solicitud') }
  }

  const toggle = (id: number) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const archiveOne = (id: number) => setConfirm({ type: 'one', ids: [id] })
  const archiveBulk = () => setConfirm({ type: 'bulk', ids: [...selected] })

  const doArchive = async () => {
    if (!confirm) return
    setActionLoading(true)
    try {
      if (confirm.ids.length === 1) await deleteDevice(confirm.ids[0])
      else await bulkDeleteDevices(confirm.ids)
      setMsg('Dispositivos archivados')
      setSelected([])
      if (detail && confirm.ids.includes(detail.id)) setDetail(null)
      load()
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || 'Error al archivar')
    } finally {
      setActionLoading(false)
      setConfirm(null)
    }
  }

  const doRestore = async (id: number) => {
    setActionLoading(true)
    try {
      await restoreDevice(id)
      setMsg('Dispositivo restaurado en el inventario')
      load()
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || 'Error al restaurar')
    } finally {
      setActionLoading(false)
    }
  }

  const openDetail = async (id: number) => {
    if (detail && detail.id === id) { setDetail(null); setDetailSoftware([]); return }
    setLoadingId(id)
    setDetail(null)
    setDetailSoftware([])
    try {
      const [dev, sw] = await Promise.all([getDevice(id), getDeviceSoftware(id)])
      setDetail(dev)
      setDetailSoftware(sw)
    } catch {
      setMsg('Error al cargar el detalle del dispositivo')
    } finally {
      setLoadingId(null)
    }
  }

  const filtered = devices.filter(d => {
    const q = search.trim().toLowerCase()
    if (q) {
      const hay = [d.ip, d.mac, d.hostname, d.name, d.vendor].map(x => (x || '').toLowerCase())
      if (!hay.some(x => x.includes(q))) return false
    }
    if (statusFilter !== 'all' && d.status !== statusFilter) return false
    return true
  })

  if (loading) return <Loading text="Cargando inventario..." />
  if (error) return <ErrorBox text={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Inventario de dispositivos</h2>
        <div className="flex gap-2">
          {selected.length > 0 && (
            <button onClick={archiveBulk} className="bg-red-600 px-4 py-2 rounded-lg text-sm">Archivar seleccionados ({selected.length})</button>
          )}
          <button onClick={discover} disabled={busy} className="bg-accent px-4 py-2 rounded-lg disabled:opacity-50">
            {busy ? 'Descubriendo...' : 'Iniciar descubrimiento'}
          </button>
        </div>
      </div>
      {agentStatus && (
        <p className={`text-sm ${agentStatus.connected ? 'text-green-400' : 'text-yellow-400'}`}>
          Agente Windows: {agentStatus.connected ? 'conectado' : 'desconectado o sin comunicación reciente'}
        </p>
      )}
      <div className="flex flex-wrap gap-3 items-center">
        <label className="flex items-center gap-2 text-sm text-slate-400">
          <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
          Mostrar dispositivos archivados
        </label>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar por IP, MAC o hostname"
          className="bg-panel px-3 py-2 rounded-lg text-sm flex-1 min-w-[220px]"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-panel px-3 py-2 rounded-lg text-sm">
          <option value="all">Todos los estados</option>
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
          <option value="unknown">Desconocido</option>
        </select>
        <button onClick={() => { setSearch(''); setStatusFilter('all') }} className="bg-slate-700 px-3 py-2 rounded-lg text-sm">Restablecer</button>
      </div>
      {msg && <p className="text-slate-300 text-sm">{msg}</p>}
      {status && <p className="text-slate-400 text-sm">Estado: {status}</p>}
      {devices.length === 0 ? <Empty text={showArchived ? 'No hay dispositivos archivados.' : 'No hay dispositivos confirmados.'} />
        : filtered.length === 0 ? <Empty text="Sin resultados para la búsqueda o filtro aplicado." /> : (
        <table className="w-full text-sm bg-panel rounded-2xl overflow-hidden border border-slate-800">
          <thead className="bg-slate-800">
            <tr>
              <th className="p-2"><input type="checkbox" onChange={e => setSelected(e.target.checked ? filtered.filter(d => !d.deleted_at).map(d => d.id) : [])} /></th>
              <th className="p-2 text-left">Equipo</th>
              <th className="p-2 text-left">Dirección IP</th>
              <th className="p-2 text-left">Dirección MAC</th>
              <th className="p-2 text-left">Hostname</th>
              <th className="p-2 text-left">Subred</th>
              <th className="p-2 text-left">Gateway</th>
              <th className="p-2 text-left">Estado</th>
              <th className="p-2 text-left">Última detección</th>
              <th className="p-2 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(d => (
              <Fragment key={d.id}>
                <tr className="border-t border-slate-700">
                  <td className="p-2">{!d.deleted_at && <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggle(d.id)} />}</td>
                  <td className="p-2">{fmt(d.name || d.hostname)}</td>
                  <td className="p-2 font-mono">{fmt(d.ip)}</td>
                  <td className="p-2 font-mono">{fmt(d.mac)}</td>
                  <td className="p-2">{fmt(d.hostname)}</td>
                  <td className="p-2 font-mono">{fmt(d.subnet)}</td>
                  <td className="p-2 font-mono">{fmt(d.gateway)}</td>
                  <td className="p-2">{d.status === 'active' ? 'Activo' : d.status === 'inactive' ? 'Inactivo' : fmt(d.status)}</td>
                  <td className="p-2">{fmtDate(d.last_seen)}</td>
                  <td className="p-2 space-x-2 whitespace-nowrap">
                    <button onClick={() => openDetail(d.id)} className="text-accent text-xs">
                      {detail && detail.id === d.id ? 'Ocultar detalle' : 'Detalle'}
                    </button>
                    {d.deleted_at
                      ? <button onClick={() => doRestore(d.id)} disabled={actionLoading} className="text-green-400 text-xs">Restaurar</button>
                      : <button onClick={() => archiveOne(d.id)} className="text-red-400 text-xs">Archivar</button>}
                  </td>
                </tr>
                {loadingId === d.id && (
                  <tr className="border-t border-slate-800 bg-slate-900/50"><td colSpan={10} className="p-3 text-xs text-slate-400">Cargando detalle...</td></tr>
                )}
                {detail && detail.id === d.id && (
                  <tr className="border-t border-slate-800 bg-slate-900/50">
                    <td colSpan={10} className="p-4">
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-semibold text-sm mb-2">Información de red</h4>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            <div><span className="text-slate-400">Equipo:</span> {fmt(detail.name || detail.hostname)}</div>
                            <div><span className="text-slate-400">Dirección IP:</span> <span className="font-mono">{fmt(detail.ip)}</span></div>
                            <div><span className="text-slate-400">Dirección MAC:</span> <span className="font-mono">{fmt(detail.mac)}</span></div>
                            <div><span className="text-slate-400">Hostname:</span> {fmt(detail.hostname)}</div>
                            <div><span className="text-slate-400">Subred:</span> <span className="font-mono">{fmt(detail.subnet)}</span></div>
                            <div><span className="text-slate-400">Gateway:</span> <span className="font-mono">{fmt(detail.gateway)}</span></div>
                            <div><span className="text-slate-400">DNS:</span> <span className="font-mono">{fmt(detail.dns)}</span></div>
                            <div><span className="text-slate-400">Sistema operativo:</span> {fmt(detail.os_info)}</div>
                            <div><span className="text-slate-400">Estado:</span> {detail.status === 'active' ? 'Activo' : detail.status === 'inactive' ? 'Inactivo' : fmt(detail.status)}</div>
                            <div><span className="text-slate-400">Última detección:</span> {fmtDate(detail.last_seen)}</div>
                            <div><span className="text-slate-400">Fabricante:</span> {fmt(detail.vendor)}</div>
                            <div><span className="text-slate-400">Fuente:</span> {fmt(detail.source)}</div>
                          </div>
                        </div>

                        <div>
                          <h4 className="font-semibold text-sm mb-2">Interfaces de red ({(detail.interfaces || []).length})</h4>
                          {(detail.interfaces || []).length === 0 ? (
                            <p className="text-xs text-slate-400">{NA}: sin datos de interfaces para este equipo (solo el equipo del agente reporta su configuración de red).</p>
                          ) : (
                            <table className="w-full text-xs">
                              <thead className="text-slate-400">
                                <tr>
                                  <th className="p-1 text-left">Interfaz</th>
                                  <th className="p-1 text-left">IP</th>
                                  <th className="p-1 text-left">MAC</th>
                                  <th className="p-1 text-left">Máscara</th>
                                  <th className="p-1 text-left">Subred</th>
                                  <th className="p-1 text-left">Gateway</th>
                                  <th className="p-1 text-left">DNS</th>
                                  <th className="p-1 text-left">Tipo</th>
                                  <th className="p-1 text-left">Estado</th>
                                </tr>
                              </thead>
                              <tbody>
                                {detail.interfaces.map((it: any) => (
                                  <tr key={it.id} className="border-t border-slate-800">
                                    <td className="p-1">{fmt(it.interface_name)}{it.is_primary ? ' (principal)' : ''}</td>
                                    <td className="p-1 font-mono">{fmt(it.ip)}</td>
                                    <td className="p-1 font-mono">{fmt(it.mac)}</td>
                                    <td className="p-1 font-mono">{fmt(it.netmask)}</td>
                                    <td className="p-1 font-mono">{fmt(it.subnet)}</td>
                                    <td className="p-1 font-mono">{fmt(it.gateway)}</td>
                                    <td className="p-1 font-mono">{fmt(it.dns)}</td>
                                    <td className="p-1">{fmt(it.interface_type)}</td>
                                    <td className="p-1">{fmt(it.status)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>

                        <div>
                          <h4 className="font-semibold text-sm mb-2">Software ({detailSoftware.length})</h4>
                          {detailSoftware.length === 0 ? (
                            <p className="text-xs text-slate-400">Sin software persistido para este dispositivo.</p>
                          ) : (
                            <ul className="grid grid-cols-1 md:grid-cols-3 gap-x-4 text-xs">
                              {detailSoftware.map((s: any) => (
                                <li key={s.id} className="text-slate-300">{s.name} <span className="text-slate-500">v{s.version || '—'}</span></li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
      {confirm && (
        <ConfirmModal
          title={confirm.ids.length === 1 ? 'Archivar dispositivo' : 'Archivar dispositivos'}
          message={`Se archivarán ${confirm.ids.length} dispositivo(s). Los datos históricos se conservarán.`}
          confirmLabel="Archivar"
          danger={false}
          loading={actionLoading}
          onConfirm={doArchive}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}
