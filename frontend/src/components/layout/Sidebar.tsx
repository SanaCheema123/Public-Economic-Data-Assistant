import { BarChart3, Bookmark, Home, MessageSquare, Settings, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Brand } from './Brand'

const nav = [
  { to: '/app', key: 'home', icon: Home, end: true },
  { to: '/app/ask', key: 'ask', icon: MessageSquare },
  { to: '/app/insights', key: 'insights', icon: BarChart3 },
  { to: '/app/saved', key: 'saved', icon: Bookmark },
  { to: '/app/settings', key: 'settings', icon: Settings },
]

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  return <>
    {open && <button className="fixed inset-0 z-40 bg-black/20 lg:hidden" aria-label="Close navigation" onClick={onClose} />}
    <aside className={`app-sidebar fixed inset-y-0 start-0 z-50 flex w-[292px] flex-col border-e bg-[#fbf8f4] lg:z-30 ${open ? 'is-open' : ''}`} style={{ borderColor: 'var(--border)' }}>
      <div className="flex h-[72px] items-center justify-between border-b px-6" style={{borderColor:'var(--border)'}}>
        <Brand />
        <button className="rounded-xl p-2 hover:bg-[#f3e9e2] lg:hidden" onClick={onClose} aria-label="Close navigation"><X className="h-5 w-5"/></button>
      </div>
      <nav className="space-y-2 px-5 py-7" aria-label="Primary navigation">
        {nav.map(({to,key,icon:Icon,end}) => <NavLink key={to} to={to} end={end} onClick={onClose}
          className={({isActive}) => `group flex items-center gap-4 rounded-2xl px-4 py-3.5 text-[15px] font-semibold transition ${isActive ? 'bg-[#eee0d7] text-[#6f4c39]' : 'text-[#29313b] hover:bg-[#f3ebe5]'}`}>
          <Icon className="h-5 w-5" strokeWidth={1.9}/><span>{t(key)}</span>
        </NavLink>)}
      </nav>
      <div className="sidebar-scene relative mt-auto min-h-[360px] border-t" style={{borderColor:'var(--border)'}} aria-hidden="true">
        <div className="absolute start-9 top-20 max-w-[140px] text-[17px] font-medium leading-tight text-[#5e4334]">
          <span className="font-serif italic">Data<br/>for a brighter<br/>Saudi Arabia</span>
        </div>
      </div>
    </aside>
  </>
}
