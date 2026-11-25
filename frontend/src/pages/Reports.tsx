import { useState } from 'react'
import { generateReport, downloadReport } from '../services/api'
import { Loading, Empty, ErrorBox } from '../components/ui/State'

export default function Reports() {
  const [msg, setMsg] = useState('')
  const [filename, setFilename] = useState('reporte_sentinelai.pdf')
  const [error, setError] = useState('')

  const gen = async () => {
    setError('')
    try { const r = await generateReport(); setFilename(r.archivo); setMsg(`Reporte generado: ${r.archivo}`) }
    catch { setError('Error al generar reporte') }
  }
  const dl = async () => {
    setError('')
    try { await downloadReport(filename); setMsg('Descarga iniciada') }
    catch { setError('Error al descargar reporte') }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Reportes</h2>
      <div className="flex gap-2">
        <button onClick={gen} className="bg-accent px-4 py-2 rounded-lg">Generar reporte PDF</button>
        <button onClick={dl} className="bg-slate-700 px-4 py-2 rounded-lg">Descargar PDF</button>
      </div>
      {msg && <p className="mt-3 text-slate-300">{msg}</p>}
      {error && <p className="mt-3 text-red-400">{error}</p>}
    </div>
  )
}