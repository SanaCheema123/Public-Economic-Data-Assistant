import { ArrowDownRight, ArrowUpRight, BarChart3, Coins, ExternalLink, Users } from 'lucide-react'
import { Sparkline } from '../charts/EconomicChart'
import { formatValue, yearOf } from '../../utils/format'

const iconMap: Record<string, any> = {
  'NY.GDP.MKTP.KD.ZG': BarChart3,
  'SL.UEM.TOTL.ZS': Users,
  'FP.CPI.TOTL.ZG': Coins,
  'SP.POP.GROW': Users,
  'SP.POP.TOTL': Users,
  'GASTAT.REAL_GDP_GROWTH': BarChart3,
  'GASTAT.SAUDI_UNEMPLOYMENT': Users,
  'GASTAT.CPI_INFLATION': Coins,
  'GASTAT.POPULATION_ESTIMATE': Users,
}

const lowerIsBetter = new Set(['FP.CPI.TOTL.ZG', 'SL.UEM.TOTL.ZS', 'GASTAT.CPI_INFLATION', 'GASTAT.SAUDI_UNEMPLOYMENT'])

type KPI = {
  indicator_id:string; name_en:string; name_ar:string; unit:string; value:number; date?:string; period_label?:string
  delta?:number|null; verification_status?:string; series?:Array<{date:string;value:number}>
  source?:{slug?:string|null;name_en?:string|null;name_ar?:string|null;url?:string|null;official?:boolean;last_sync?:string|null}
}

export function KPICard({ item, language = 'en' }: { item: KPI; language?:'en'|'ar' }) {
  const Icon = iconMap[item.indicator_id] || BarChart3
  const delta = item.delta
  const good = delta == null ? true : (lowerIsBetter.has(item.indicator_id) ? delta <= 0 : delta >= 0)
  const sourceName = language === 'ar' ? (item.source?.name_ar || item.source?.name_en) : item.source?.name_en
  const badge = item.source?.official ? (language === 'ar' ? 'رسمي مباشر' : 'OFFICIAL LIVE') : (item.source?.slug === 'world-bank' ? 'WORLD BANK LIVE' : 'LIVE')
  return <article className="glass-card min-h-[186px] p-5">
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-center gap-3"><span className="icon-bubble"><Icon className="h-5 w-5"/></span><div><h3 className="font-extrabold">{language==='ar'?item.name_ar:item.name_en}</h3><p className="text-xs muted">{language==='ar'?item.name_en:item.name_ar}</p></div></div>
      {item.verification_status==='verified' && <span className="live-badge whitespace-nowrap">{badge}</span>}
    </div>
    <div className="mt-3 flex items-end justify-between gap-3">
      <div>
        <div className="text-[34px] font-black tracking-tight">{formatValue(item.value,item.unit)}</div>
        <div className="mt-1 text-xs muted">{item.period_label || yearOf(item.date)} {language==='ar'?'• أحدث قيمة منشورة':'• latest published'}</div>
        {sourceName && <div className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-[#805d49]">
          {item.source?.url ? <a className="inline-flex items-center gap-1 hover:underline" href={item.source.url} target="_blank" rel="noreferrer">{sourceName}<ExternalLink className="h-3 w-3"/></a> : sourceName}
        </div>}
      </div>
      <div className="flex flex-col items-end gap-1">
        {delta != null && <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${good?'bg-emerald-50 text-emerald-700':'bg-red-50 text-red-700'}`}>{delta>=0?<ArrowUpRight className="h-3.5 w-3.5"/>:<ArrowDownRight className="h-3.5 w-3.5"/>}{delta>0?'+':''}{delta.toFixed(1)}</span>}
        {(item.series?.length ?? 0) > 1 && <Sparkline values={(item.series??[]).map(v=>v.value)} positive={good}/>} 
      </div>
    </div>
  </article>
}
