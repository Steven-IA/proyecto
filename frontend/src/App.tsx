import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Server, Network, Brain, ShieldAlert, Bell, History, FileText, Settings, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import Overview from './pages/Overview'
import Inventory from './pages/Inventory'
import Topology from './pages/Topology'
import AI from './pages/AI'
import Vulnerabilities from './pages/Vulnerabilities'
import Alerts from './pages/Alerts'
import HistoryPage from './pages/History'
import Reports from './pages/Reports'
import SettingsPage from './pages/Settings'

const nav = [
  { to: '/', label: 'Resumen', icon: LayoutDashboard },
  { to: '/inventory', label: 'Inventario', icon: Server },
  { to: '/topology', label: 'Topología', icon: Network },
  { to: '/ai', label: 'Inteligencia Artificial', icon: Brain },
  { to: '/vulns', label: 'Vulnerabilidades', icon: ShieldAlert },
  { to: '/alerts', label: 'Alertas', icon: Bell },
  { to: '/history', label: 'Historial', icon: History },
  { to: '/reports', label: 'Reportes', icon: FileText },
  { to: '/settings', label: 'Configuración', icon: Settings },
]

export default function App() {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div className="flex min-h-screen bg-bg">
      <aside className={`${collapsed ? 'w-20' : 'w-64'} bg-panel border-r border-slate-800 p-4 transition-all duration-200 flex flex-col`}>
        <div className="flex items-center justify-between mb-6">
          {!collapsed && <h1 className="text-xl font-bold text-accent">SentinelAI</h1>}
          <button onClick={() => setCollapsed(!collapsed)} className="text-slate-400 hover:text-white">
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        <nav className="space-y-1 flex-1">
          {nav.map(n => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition ${isActive ? 'bg-accent text-white shadow' : 'text-slate-300 hover:bg-slate-800'}`}>
              <n.icon size={18} />
              {!collapsed && <span>{n.label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/topology" element={<Topology />} />
          <Route path="/ai" element={<AI />} />
          <Route path="/vulns" element={<Vulnerabilities />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}