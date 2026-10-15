import { ExternalLink, Landmark } from 'lucide-react'

export type SourceCardData = { id:string; name_en:string; name_ar:string; url:string; slug?:string; datasets?:Array<{verification_status:string}> }

export function SourceCards({ sources, language='en' }: { sources: SourceCardData[]; language?: 'en'|'ar' }) {
  return <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
    {sources.map(source=><a key={source.id} href={source.url} target="_blank" rel="noreferrer" className="group rounded-2xl border bg-white/70 p-3 text-center transition hover:-translate-y-0.5 hover:shadow-card" style={{borderColor:'var(--border)'}}>
      <span className="mx-auto grid h-9 w-9 place-items-center rounded-xl bg-[#f5ebe1] text-[#7c5a47]"><Landmark className="h-4 w-4"/></span>
      <div className="mt-2 text-xs font-bold leading-tight">{language==='ar'?source.name_ar:source.name_en}</div>
      <ExternalLink className="mx-auto mt-2 h-3.5 w-3.5 opacity-0 transition group-hover:opacity-60"/>
    </a>)}
  </div>
}
