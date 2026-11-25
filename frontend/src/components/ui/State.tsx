export function Loading({ text = 'Cargando...' }: { text?: string }) {
  return <div className="text-slate-400 animate-pulse">{text}</div>
}
export function Empty({ text }: { text: string }) {
  return <div className="text-center py-10 text-slate-400">{text}</div>
}
export function ErrorBox({ text }: { text: string }) {
  return <div className="text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl p-3">{text}</div>
}