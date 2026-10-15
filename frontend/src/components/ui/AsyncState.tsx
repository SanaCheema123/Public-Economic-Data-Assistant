import { AlertCircle, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

export function LoadingCard({ label = 'Loading…' }: { label?: string }) {
  return <div className="glass-card grid min-h-40 place-items-center p-8"><div className="flex items-center gap-3 text-sm muted"><LoaderCircle className="h-5 w-5 animate-spin" />{label}</div></div>
}

export function ErrorCard({ message, action }: { message: string; action?: ReactNode }) {
  return <div className="glass-card flex min-h-40 flex-col items-center justify-center gap-3 p-8 text-center"><AlertCircle className="h-7 w-7 text-amber-700"/><p className="max-w-xl text-sm muted">{message}</p>{action}</div>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-2xl bg-[#eee5de] ${className}`} />
}
