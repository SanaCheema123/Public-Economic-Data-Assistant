import type { ReactNode } from 'react'

export function PageHero({ title, arabic, description, children }: { title: string; arabic?: string; description?: string; children?: ReactNode }) {
  return <section className="saudi-scene relative overflow-hidden border-b px-5 py-7 md:px-8 lg:px-10" style={{borderColor:'var(--border)'}}>
    <div className="relative z-10 flex min-h-[120px] items-center justify-between gap-6">
      <div className="max-w-3xl"><h1 className="text-3xl font-black tracking-tight md:text-[38px]">{title}</h1>{arabic && <div className="mt-1 text-lg font-semibold text-[#784f3c]" dir="rtl">{arabic}</div>}{description && <p className="mt-2 max-w-2xl text-sm md:text-base muted">{description}</p>}</div>
      {children && <div className="hidden md:block">{children}</div>}
    </div>
  </section>
}
