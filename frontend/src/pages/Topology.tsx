import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Controls, MiniMap, Background, BackgroundVariant, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { getDevices, getAgentStatus } from '../services/api'
import NetworkNode from '../components/topology/NetworkNode'
import { Loading, Empty, ErrorBox } from '../components/ui/State'

const nodeTypes = { network: NetworkNode }

function typeOf(d: any): string {
  const t = (d.device_type || '').toLowerCase()
  if (t.includes('servidor')) return 'servidor'
  if (t.includes('impresora')) return 'impresora'
  if (t.includes('movil') || t.includes('celular') || t.includes('telefono')) return 'movil'
  if (t === 'desconocido') return 'desconocido'
  return 'computador'
}

function realName(d: any): string {
  const h = String(d.name || d.hostname || '').trim()
  if (h && h.toLowerCase() !== 'no disponible') return h
  return 'Sin hostname'
}

export default function Topology() {
  const [devices, setDevices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [agent, setAgent] = useState<any>(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [riskFilter, setRiskFilter] = useState('all')
  const [selected, setSelected] = useState<any>(null)

  const load = () => {
    getDevices().then(setDevices).catch(() => setError('No se pudo cargar la topología'))
    getAgentStatus().then(setAgent).catch(() => setAgent({ connected: false }))
    setLoading(false)
  }
  useEffect(() => {
    load()
    const t = setInterval(load, 10000)
    return () => clearInterval(t)
  }, [])

  const filtered = useMemo(() => {
    return devices.filter(d => {
      const q = search.toLowerCase()
      if (q && !(d.ip.includes(q) || (d.mac || '').toLowerCase().includes(q) || (d.hostname || '').toLowerCase().includes(q) || (d.name || '').toLowerCase().includes(q))) return false
      if (typeFilter !== 'all' && typeOf(d) !== typeFilter) return false
      if (statusFilter !== 'all' && d.status !== statusFilter) return false
      if (riskFilter !== 'all' && (d.risk_level || 'bajo') !== riskFilter) return false
      return true
    })
  }, [devices, search, typeFilter, statusFilter, riskFilter])

  const { nodes, edges } = useMemo(() => {
    const ns: any[] = []
    const es: any[] = []
    const rootId = 'agent-root'
    ns.push({
      id: rootId,
      type: 'network',
      position: { x: 400, y: 250 },
      data: { label: 'Equipo de descubrimiento', ip: 'Agente SentinelAI', type: 'agente', status: agent?.connected ? 'active' : 'inactive', risk_level: null },
    })
    const r = 220
    filtered.forEach((d, i) => {
      const ang = (i / Math.max(filtered.length, 1)) * Math.PI * 2
      const x = 400 + r * Math.cos(ang)
      const y = 250 + r * Math.sin(ang)
      ns.push({
        id: `dev-${d.id}`,
        type: 'network',
        position: { x, y },
        data: { label: realName(d), ip: d.ip, type: typeOf(d), status: d.status, risk_level: d.risk_level },
      })
      es.push({
        id: `e-${d.id}`,
        source: rootId,
        target: `dev-${d.id}`,
        animated: d.status === 'active',
        style: { stroke: d.status === 'active' ? '#22c55e' : '#64748b' },
        label: 'descubierto por agente (relación lógica estimada)',
        labelStyle: { fill: '#94a3b8', fontSize: 9 },
      })
    })
    return { nodes: ns, edges: es }
  }, [filtered, agent])

  const [nodesState, setNodes, onNodesChange] = useNodesState(nodes)
  const [edgesState, setEdges, onEdgesChange] = useEdgesState(edges)

  useEffect(() => { setNodes(nodes); setEdges(edges) }, [nodes, edges, setNodes, setEdges])

  const stats = useMemo(() => ({
    total: devices.length,
    active: devices.filter(d => d.status === 'active').length,
    inactive: devices.filter(d => d.status === 'inactive').length,
    risk: devices.filter(d => d.risk_level && d.risk_level !== 'bajo').length,
    unknown: devices.filter(d => (d.device_type || '').toLowerCase() === 'desconocido').length,
  }), [devices])

  if (loading) return <Loading text="Cargando topología..." />
  if (error) return <ErrorBox text={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Topología de red</h2>
          <p className="text-slate-400 text-sm">Visualización y análisis de la infraestructura de red (relaciones lógicas estimadas).</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="bg-slate-700 px-3 py-2 rounded-lg text-sm">Actualizar</button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Confirmados', value: stats.total },
          { label: 'Activos', value: stats.active },
          { label: 'Inactivos', value: stats.inactive },
          { label: 'Con riesgo', value: stats.risk },
          { label: 'Desconocidos', value: stats.unknown },
        ].map(k => (
          <div key={k.label} className="bg-panel p-3 rounded-xl">
            <p className="text-2xl font-bold">{k.value}</p>
            <p className="text-xs text-slate-400">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-3 items-center flex-wrap">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar IP o nombre" className="bg-panel px-3 py-2 rounded-lg text-sm" />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="bg-panel px-3 py-2 rounded-lg text-sm">
          <option value="all">Todos los tipos</option>
          <option value="computador">Computador</option>
          <option value="servidor">Servidor</option>
          <option value="impresora">Impresora</option>
          <option value="movil">Móvil</option>
          <option value="desconocido">Desconocido</option>
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-panel px-3 py-2 rounded-lg text-sm">
          <option value="all">Todos los estados</option>
          <option value="active">Activo</option>
          <option value="inactive">Inactivo</option>
        </select>
        <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)} className="bg-panel px-3 py-2 rounded-lg text-sm">
          <option value="all">Todos los riesgos</option>
          <option value="bajo">Bajo</option>
          <option value="medio">Medio</option>
          <option value="alto">Alto</option>
        </select>
        <button onClick={() => { setSearch(''); setTypeFilter('all'); setStatusFilter('all'); setRiskFilter('all') }} className="bg-slate-700 px-3 py-2 rounded-lg text-sm">Restablecer</button>
      </div>

      {devices.length === 0 ? (
        <Empty text="No hay dispositivos confirmados. Ejecuta un descubrimiento para poblar la topología." />
      ) : (
        <div className="bg-panel rounded-xl overflow-hidden" style={{ height: 520 }}>
          <ReactFlow
            nodes={nodesState}
            edges={edgesState}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => {
              const dev = devices.find(d => `dev-${d.id}` === node.id)
              if (dev) setSelected(dev)
              else if (node.id === 'agent-root') setSelected({ hostname: 'Equipo de descubrimiento', ip: 'Agente SentinelAI', mac: 'No disponible', vendor: 'SentinelAI', device_type: 'agente', status: agent?.connected ? 'active' : 'inactive', risk_level: null, last_seen: null, source: 'agente' })
            }}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#1e293b" />
            <Controls />
            <MiniMap nodeColor={() => '#3b82f6'} maskColor="rgba(0,0,0,0.6)" />
          </ReactFlow>
        </div>
      )}

      {selected && (
        <div className="bg-panel p-4 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">Detalles del dispositivo</h3>
            <button onClick={() => setSelected(null)} className="text-slate-400 text-sm">Cerrar</button>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-slate-400">Equipo:</span> {selected.name || selected.hostname || 'No disponible'}</div>
            <div><span className="text-slate-400">Hostname:</span> {selected.hostname || 'No disponible'}</div>
            <div><span className="text-slate-400">IP:</span> {selected.ip}</div>
            <div><span className="text-slate-400">MAC:</span> {selected.mac || 'No disponible'}</div>
            <div><span className="text-slate-400">Subred:</span> {selected.subnet || 'No disponible'}</div>
            <div><span className="text-slate-400">Gateway:</span> {selected.gateway || 'No disponible'}</div>
            <div><span className="text-slate-400">Fabricante:</span> {selected.vendor || 'Desconocido'}</div>
            <div><span className="text-slate-400">Tipo:</span> {selected.device_type || 'desconocido'}</div>
            <div><span className="text-slate-400">Estado:</span> {selected.status}</div>
            <div><span className="text-slate-400">Riesgo:</span> {selected.risk_level || 'No disponible'}</div>
            <div><span className="text-slate-400">Fuente:</span> {selected.source || 'No disponible'}</div>
            <div><span className="text-slate-400">Última detección:</span> {selected.last_seen ? new Date(selected.last_seen).toLocaleString() : 'No disponible'}</div>
          </div>
        </div>
      )}

      <div className="bg-panel p-4 rounded-xl">
        <h3 className="font-semibold mb-2">Leyenda</h3>
        <div className="flex flex-wrap gap-4 text-xs text-slate-400">
          <span>● Activo</span>
          <span>● Inactivo</span>
          <span>— Relación lógica estimada</span>
        </div>
      </div>
    </div>
  )
}