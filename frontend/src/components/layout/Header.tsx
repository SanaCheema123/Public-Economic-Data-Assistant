import { Bell, ChevronDown, Menu, Search, X } from 'lucide-react'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { get } from '../../api/client'
import { useAuth } from '../../services/auth'

type SearchResult = {
  indicators: Array<{id:string;name_en:string;name_ar:string;unit:string;category:string}>
  datasets: Array<{id:string;name_en:string;name_ar:string;verification_status:string}>
  sources: Array<{id:string;name_en:string;name_ar:string;url:string}>
  insights: Array<{id:string;title_en:string;title_ar:string}>
  saved: Array<{id:string;title:string;item_type:string}>
}

export function Header({ onMenu }: { onMenu: () => void }) {
  const { t, i18n } = useTranslation()
  const { user, updateLanguage } = useAuth()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [focused, setFocused] = useState(false)
  const [notifications, setNotifications] = useState(false)
  const language = i18n.language === 'ar' ? 'ar' : 'en'
  const results = useQuery({
    queryKey: ['global-search', search],
    queryFn: () => get<SearchResult>(`/api/search?q=${encodeURIComponent(search)}`),
    enabled: search.trim().length >= 2,
    staleTime: 30_000
  })
  const submitSearch = () => {
    if (!search.trim()) return
    navigate(`/app/ask?q=${encodeURIComponent(search.trim())}`)
    setSearch('')
  }
  const initials = user?.full_name?.split(' ').map(x=>x[0]).slice(0,2).join('').toUpperCase() || 'U'
  const flat = [
    ...(results.data?.indicators ?? []).map(x=>({label:language==='ar'?x.name_ar:x.name_en, type:'Indicator'})),
    ...(results.data?.datasets ?? []).map(x=>({label:language==='ar'?x.name_ar:x.name_en, type:'Dataset'})),
    ...(results.data?.saved ?? []).map(x=>({label:x.title, type:'Saved'})),
  ].slice(0,6)
  return <header className="fixed inset-x-0 top-0 z-20 h-[72px] border-b bg-[#fcfaf7]/95 backdrop-blur-xl lg:start-[292px]" style={{borderColor:'var(--border)'}}>
    <div className="flex h-full items-center gap-3 px-4 md:px-7">
      <button className="rounded-xl p-2 hover:bg-[#f2e8e1] lg:hidden" onClick={onMenu} aria-label="Open navigation"><Menu className="h-5 w-5"/></button>
      <div className="relative max-w-[760px] flex-1">
        <form onSubmit={(e)=>{e.preventDefault();submitSearch()}} className="flex h-11 items-center rounded-full border bg-white/75 px-4 shadow-sm" style={{borderColor:'var(--border)'}}>
          <Search className="h-4 w-4 text-[#7a6e68]"/><input value={search} onChange={e=>setSearch(e.target.value)} onFocus={()=>setFocused(true)} onBlur={()=>window.setTimeout(()=>setFocused(false),150)} className="w-full bg-transparent px-3 text-sm outline-none" placeholder={t('searchPlaceholder')} aria-label={t('searchPlaceholder')}/>
          {search && <button type="button" onClick={()=>setSearch('')} className="rounded-full p-1 text-[#877970]" aria-label="Clear search"><X className="h-4 w-4"/></button>}
        </form>
        {focused && search.trim().length>=2 && <div className="glass-card absolute inset-x-0 top-12 z-50 overflow-hidden p-2">
          {results.isLoading && <div className="px-3 py-3 text-sm muted">{t('loading')}</div>}
          {!results.isLoading && flat.length===0 && <div className="px-3 py-3 text-sm muted">{t('noResults')}</div>}
          {flat.map((item,idx)=><button key={`${item.type}-${idx}`} onMouseDown={()=>{setSearch(item.label);navigate(`/app/ask?q=${encodeURIComponent(item.label)}`)}} className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-start text-sm hover:bg-[#f5ede7]"><span>{item.label}</span><span className="text-[10px] uppercase tracking-wider text-[#9a8a80]">{item.type}</span></button>)}
        </div>}
      </div>
      <div className="ms-auto flex items-center gap-2">
        <div className="hidden rounded-full border bg-white/70 p-1 sm:flex" style={{borderColor:'var(--border)'}}>
          <button onClick={()=>void updateLanguage('en')} className={`rounded-full px-3 py-1.5 text-xs font-bold ${language==='en'?'bg-[#efe1d7] text-[#704e3d]':''}`}>EN</button>
          <button onClick={()=>void updateLanguage('ar')} className={`rounded-full px-3 py-1.5 text-xs font-bold ${language==='ar'?'bg-[#efe1d7] text-[#704e3d]':''}`}>AR</button>
        </div>
        <div className="relative">
          <button onClick={()=>setNotifications(v=>!v)} className="relative rounded-full p-2.5 hover:bg-[#f3e9e2]" aria-label="Notifications"><Bell className="h-5 w-5"/><span className="absolute end-2 top-2 h-2 w-2 rounded-full bg-[#b56d5d]"/></button>
          {notifications && <div className="glass-card absolute end-0 top-12 w-72 p-4 text-sm"><div className="font-bold">Notifications</div><p className="mt-2 text-xs muted">No new notifications. Data-source synchronization alerts will appear here.</p></div>}
        </div>
        <button onClick={()=>navigate('/app/settings')} className="hidden items-center gap-2 rounded-full p-1.5 pe-2 hover:bg-[#f3e9e2] md:flex">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#b7917b] text-xs font-bold text-white">{initials}</span><span className="max-w-28 truncate text-sm font-semibold">{user?.full_name}</span><ChevronDown className="h-4 w-4"/>
        </button>
      </div>
    </div>
  </header>
}
