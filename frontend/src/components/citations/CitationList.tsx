import { ExternalLink, FileWarning, ShieldCheck } from 'lucide-react'
import type { Citation } from '../../types/api'

export function CitationList({ citations, language='en' }: { citations:Citation[]; language?:'en'|'ar' }) {
  if (!citations.length) return null
  return <div className="space-y-2">
    {citations.map((c,index)=>{
      const verified=c.verification_status==='verified'
      const href=c.url
      return <div key={c.id ?? `${c.title}-${index}`} className="flex items-start gap-3 rounded-2xl border bg-[#fbf8f4] p-3" style={{borderColor:'var(--border)'}}>
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white text-[#7c5a47]">{verified?<ShieldCheck className="h-4 w-4"/>:<FileWarning className="h-4 w-4"/>}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-bold">{language==='ar'?(c.indicator_name_ar||c.title):(c.indicator_name||c.title)}</span>
            <span className={verified?'live-badge':'rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-extrabold text-amber-800'}>{verified?'VERIFIED':'UNVERIFIED'}</span>
          </div>
          <p className="mt-1 text-xs muted">{language==='ar'?(c.source_name_ar||c.source_name):c.source_name} • {language==='ar'?(c.dataset_name_ar||c.dataset_name):c.dataset_name}{c.period?` • ${c.period}`:''}</p>
        </div>
        {href&&<a href={href} target={href.startsWith('http')?'_blank':undefined} rel="noreferrer" className="rounded-xl p-2 hover:bg-white" aria-label="View source"><ExternalLink className="h-4 w-4"/></a>}
      </div>
    })}
  </div>
}
