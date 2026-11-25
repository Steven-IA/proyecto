import { Handle, Position, NodeProps } from '@xyflow/react'
import { Server, Monitor, Printer, Smartphone, HelpCircle, Shield, Wifi } from 'lucide-react'

const ICONS: Record<string, any> = {
  gateway: Wifi,
  agente: Shield,
  computador: Monitor,
  servidor: Server,
  impresora: Printer,
  movil: Smartphone,
  desconocido: HelpCircle,
}

export default function NetworkNode({ data }: NodeProps) {
  const d = data as any
  const Icon = ICONS[d.type] || HelpCircle
  const active = d.status === 'active'
  const risk = d.risk_level
  return (
    <div className="bg-panel border border-slate-700 rounded-xl px-3 py-2 min-w-[150px] shadow-lg">
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center gap-2">
        <div className={`p-1.5 rounded-lg ${active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          <Icon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold truncate">{String(d.label ?? '')}</div>
          <div className="text-[10px] text-slate-400 truncate">{String(d.ip ?? '')}</div>
        </div>
        {risk && risk !== 'bajo' && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${risk === 'alto' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
            {String(risk)}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}