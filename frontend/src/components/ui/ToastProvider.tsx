import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'

type Toast = { id: number; message: string; type: 'success' | 'error' }
const ToastContext = createContext<{ show: (message: string, type?: Toast['type']) => void } | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const show = (message: string, type: Toast['type'] = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((items) => [...items, { id, message, type }])
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 3200)
  }
  const value = useMemo(() => ({ show }), [])
  return <ToastContext.Provider value={value}>
    {children}
    <div className="fixed z-[100] top-5 end-5 space-y-3" aria-live="polite">
      {toasts.map((toast) => <div key={toast.id} className="glass-card flex max-w-sm items-center gap-3 px-4 py-3 text-sm font-semibold">
        {toast.type === 'success' ? <CheckCircle2 className="h-5 w-5 text-emerald-700" /> : <XCircle className="h-5 w-5 text-red-700" />}
        <span>{toast.message}</span>
      </div>)}
    </div>
  </ToastContext.Provider>
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used inside ToastProvider')
  return value
}
