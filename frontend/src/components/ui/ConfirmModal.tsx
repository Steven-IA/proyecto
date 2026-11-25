import { useState } from 'react'

export default function ConfirmModal({ title, message, confirmLabel, danger = true, loading = false, onConfirm, onCancel }: any) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-panel border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-lg font-bold mb-2">{title}</h3>
        <p className="text-slate-300 text-sm mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} disabled={loading} className="px-4 py-2 rounded-lg bg-slate-700 text-sm">Cancelar</button>
          <button onClick={onConfirm} disabled={loading} className={`px-4 py-2 rounded-lg text-sm text-white ${danger ? 'bg-red-600' : 'bg-accent'}`}>
            {loading ? 'Procesando...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}