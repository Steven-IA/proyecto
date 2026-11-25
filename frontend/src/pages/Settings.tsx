import { useEffect, useState } from 'react'
import { getSettings, updateSetting } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { getSettings().then(setSettings).finally(() => setLoading(false)) }, [])

  const save = async (key: string, value: string) => {
    try { await updateSetting(key, value); setMsg('Configuración guardada'); setSettings({ ...settings, [key]: value }) }
    catch (e: any) { setError(e?.response?.data?.detail || 'Error al guardar') }
  }

  if (loading) return <Loading text="Cargando configuración..." />

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Configuración</h2>
      {msg && <p className="text-green-400 mb-2">{msg}</p>}
      {error && <p className="text-red-400 mb-2">{error}</p>}
      <div className="space-y-4 max-w-xl">
        <div className="bg-panel p-4 rounded-xl">
          <label className="block mb-1">Subred autorizada</label>
          <input defaultValue={settings.authorized_subnet} id="subnet" className="w-full bg-slate-800 px-3 py-2 rounded" />
          <button onClick={() => save('authorized_subnet', (document.getElementById('subnet') as HTMLInputElement).value)} className="mt-2 bg-accent px-4 py-2 rounded">Guardar</button>
        </div>
        <div className="bg-panel p-4 rounded-xl">
          <label className="block mb-1">Intervalo de descubrimiento (minutos)</label>
          <input type="number" defaultValue={settings.discovery_interval_minutes} id="interval" className="w-full bg-slate-800 px-3 py-2 rounded" />
          <button onClick={() => save('discovery_interval_minutes', (document.getElementById('interval') as HTMLInputElement).value)} className="mt-2 bg-accent px-4 py-2 rounded">Guardar</button>
        </div>
        <div className="bg-panel p-4 rounded-xl">
          <label className="block mb-1">Agente habilitado</label>
          <select defaultValue={settings.agent_enabled} id="agent" className="w-full bg-slate-800 px-3 py-2 rounded">
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>
          <button onClick={() => save('agent_enabled', (document.getElementById('agent') as HTMLSelectElement).value)} className="mt-2 bg-accent px-4 py-2 rounded">Guardar</button>
        </div>
      </div>
    </div>
  )
}