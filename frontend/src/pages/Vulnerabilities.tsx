import { useEffect, useState } from 'react'
import { getVulns, deleteVulnerability, bulkDeleteVulnerabilities } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'
import ConfirmModal from '../components/ui/ConfirmModal'

export default function Vulnerabilities() {
  const [vulns, setVulns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [confirm, setConfirm] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const toggle = (id: number) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const load = () => { setLoading(true); getVulns().then(setVulns).catch(() => setError('Error al cargar vulnerabilidades')).finally(() => setLoading(false)) }
  useEffect(load, [])

  const removeOne = (id: number) => setConfirm({ ids: [id] })
  const removeBulk = () => setConfirm({ ids: [...selected] })

  const doDelete = async () => {
    if (!confirm) return
    setBusy(true)
    try {
      if (confirm.ids.length === 1) await deleteVulnerability(confirm.ids[0])
      else {
        const r = await bulkDeleteVulnerabilities(confirm.ids)
        setMsg(`Eliminadas: ${r.eliminados}, no encontradas: ${r.no_encontrados}`)
      }
      if (confirm.ids.length === 1) setMsg('Vulnerabilidad eliminada')
      setSelected([])
      load()
    } catch (e: any) { setMsg(e?.response?.data?.detail || 'Error al eliminar') }
    finally { setBusy(false); setConfirm(null) }
  }

  if (loading) return <Loading text="Cargando vulnerabilidades..." />
  if (error) return <ErrorBox text={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Vulnerabilidades</h2>
        {selected.length > 0 && <button onClick={removeBulk} className="bg-red-600 px-4 py-2 rounded-lg text-sm">Eliminar seleccionadas ({selected.length})</button>}
      </div>
      {msg && <p className="text-slate-300 text-sm">{msg}</p>}
      {vulns.length === 0 ? <Empty text="No hay vulnerabilidades registradas." /> : (
        <table className="w-full text-sm bg-panel rounded-2xl overflow-hidden border border-slate-800">
          <thead className="bg-slate-800"><tr>
            <th className="p-2"><input type="checkbox" onChange={e => setSelected(e.target.checked ? vulns.map(v => v.id) : [])} /></th>
            <th className="p-2 text-left">CVE</th><th className="p-2 text-left">Software</th><th className="p-2 text-left">Severidad</th><th className="p-2 text-left">Nivel</th><th className="p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>{vulns.map(v => (
            <tr key={v.id} className="border-t border-slate-700">
              <td className="p-2"><input type="checkbox" checked={selected.includes(v.id)} onChange={() => toggle(v.id)} /></td>
              <td className="p-2">{v.cve_id}</td><td className="p-2">{v.software}</td><td className="p-2">{v.severity}</td><td className="p-2">{v.verification_level}</td>
              <td className="p-2"><button onClick={() => removeOne(v.id)} className="text-red-400 text-xs">Eliminar</button></td>
            </tr>
          ))}</tbody>
        </table>
      )}
      {confirm && (
        <ConfirmModal title="Eliminar vulnerabilidades" message={`Se eliminarán ${confirm.ids.length} vulnerabilidad(es) permanentemente.`} confirmLabel="Eliminar" loading={busy} onConfirm={doDelete} onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}