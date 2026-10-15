import { BarChart3 } from 'lucide-react'

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="flex items-center gap-3">
    <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#efe1d7] text-[#876450]"><BarChart3 className="h-6 w-6" strokeWidth={2.2}/></div>
    {!compact && <div className="min-w-0">
      <div className="truncate text-sm font-extrabold tracking-tight">Public Economic Data Assistant</div>
      <div className="truncate text-[11px] text-[#766d68]" dir="rtl">المساعد الذكي للبيانات الاقتصادية العامة</div>
    </div>}
  </div>
}
