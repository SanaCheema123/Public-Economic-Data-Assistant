import { BarChart3, Filter, Sparkles, Wifi } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { get } from '../../api/client'
import type { ChartSpec, InsightsPayload } from '../../types/api'
import { PageHero } from '../../components/layout/PageHero'
import { KPICard } from '../../components/cards/KPICard'
import { EconomicChart } from '../../components/charts/EconomicChart'
import { SourceCards, type SourceCardData } from '../../components/sources/SourceCards'
import { ErrorCard, Skeleton } from '../../components/ui/AsyncState'

const categories = [
  ['All','all'], ['Economy','Economy'], ['Population','Population'], ['Labor Market','Labor Market'], ['Prices','Prices']
]
const trendCodes = ['NY.GDP.MKTP.KD.ZG','FP.CPI.TOTL.ZG','SL.UEM.TOTL.ZS']
const headlineGroups = [
  ['GASTAT.REAL_GDP_GROWTH','NY.GDP.MKTP.KD.ZG'],
  ['GASTAT.CPI_INFLATION','FP.CPI.TOTL.ZG'],
  ['GASTAT.SAUDI_UNEMPLOYMENT','SL.UEM.TOTL.ZS'],
]

export default function InsightsPage(){
  const {t,i18n}=useTranslation(); const language=i18n.language==='ar'?'ar':'en'
  const [category,setCategory]=useState('all'); const [years,setYears]=useState(5)
  const query=useQuery({queryKey:['insights',category,years],queryFn:()=>get<InsightsPayload>(`/api/insights?category=${encodeURIComponent(category)}&years=${years}`),refetchInterval:5*60*1000})
  const sources=useQuery({queryKey:['sources'],queryFn:()=>get<Array<SourceCardData & {source_type:string}>>('/api/sources')})
  const data=query.data
  const trendSpec=useMemo<ChartSpec|null>(()=>{
    if(!data)return null
    const candidates=data.series.filter(s=>trendCodes.includes(s.indicator_id))
    if(!candidates.length)return null
    return {type:'grouped_bar',title:'Economic trends',title_ar:'الاتجاهات الاقتصادية',x:[],y:[],labels:[],values:[],series:candidates.map(s=>({name:language==='ar'?s.name_ar:s.name_en,x:s.values.map(v=>v.date.slice(0,4)),y:s.values.map(v=>v.value)})),x_label:language==='ar'?'السنة':'Year',y_label:'%'}
  },[data,language])
  const comparisonSpec=useMemo<ChartSpec|null>(()=>{
    if(!data)return null
    const rates=headlineGroups.map(group=>group.map(code=>data.cards.find(c=>c.indicator_id===code)).find(Boolean)).filter(Boolean) as InsightsPayload['cards']
    if(!rates.length)return null
    return {type:'bar',title:'Latest available rates',title_ar:'أحدث المعدلات المتاحة',x:rates.map(c=>language==='ar'?c.name_ar:c.name_en),y:rates.map(c=>c.value),series:[],labels:[],values:[],x_label:'',y_label:'%'}
  },[data,language])
  const displayCards=headlineGroups.map(group=>group.map(code=>(data?.cards??[]).find(c=>c.indicator_id===code)).find(Boolean)).filter(Boolean) as InsightsPayload['cards']
  return <div>
    <PageHero title={t('insightsTitle')} arabic={language==='en'?'الرؤى والتحليلات':'Insights'} description={t('insightsSub')}/>
    <div className="space-y-4 p-4 md:p-6 lg:p-8">
      <section className="glass-card flex flex-col gap-4 p-4 lg:flex-row lg:items-center">
        <div className="flex items-center gap-3"><span className="icon-bubble !h-10 !w-10"><Filter className="h-4 w-4"/></span><div><div className="text-xs font-bold">{t('period')}</div><select value={years} onChange={e=>setYears(Number(e.target.value))} className="mt-1 rounded-xl border bg-white px-3 py-2 text-sm outline-none" style={{borderColor:'var(--border)'}}><option value={3}>Last 3 Years</option><option value={5}>Last 5 Years</option><option value={10}>Last 10 Years</option></select></div></div>
        <div className="h-px bg-[#e6ddd6] lg:h-12 lg:w-px"/>
        <div className="min-w-0 flex-1"><div className="mb-2 text-xs font-bold">{t('category')}</div><div className="flex flex-wrap gap-2">{categories.map(([label,value])=><button key={value} onClick={()=>setCategory(value)} className={`rounded-2xl border px-3.5 py-2 text-xs font-semibold transition ${category===value?'bg-[#e9d9cf] text-[#6f4d3b]':'bg-white/60 hover:bg-[#f7eee8]'}`} style={{borderColor:'var(--border)'}}>{label}</button>)}</div></div>
        {data?.data_status.ready&&<span className="live-badge shrink-0"><Wifi className="h-3 w-3"/> LIVE DATA</span>}
      </section>
      {query.isError&&<ErrorCard message="Live insights could not be loaded. Please check the backend and source synchronization." action={<button className="soft-button" onClick={()=>query.refetch()}>Retry</button>}/>} 
      <section className="grid gap-4 lg:grid-cols-3">{query.isLoading?Array.from({length:3}).map((_,i)=><Skeleton key={i} className="h-[172px]"/>):displayCards.map(card=>{
        const series=data?.series.find(s=>s.id===card.id)?.values??[]; const delta=series.length>1?card.value-series[series.length-2].value:null
        return <KPICard key={card.id} language={language} item={{...card,delta,series:series.map(v=>({date:v.date,value:v.value}))}}/>
      })}</section>
      {data&&<div className="grid gap-4 xl:grid-cols-[1.4fr_.8fr]">
        <section className="glass-card p-5"><div className="flex items-center justify-between"><div className="flex items-center gap-3"><span className="icon-bubble !h-10 !w-10"><BarChart3 className="h-4 w-4"/></span><div><h2 className="font-extrabold">GDP Growth, Inflation & Unemployment</h2><p className="text-xs muted" dir="rtl">الناتج المحلي والتضخم والبطالة</p></div></div><span className="live-badge">VERIFIED</span></div>{trendSpec?<EconomicChart spec={trendSpec} height={320}/>:<div className="grid h-72 place-items-center text-sm muted">No synchronized time-series indicators in this filter.</div>}</section>
        <section className="glass-card p-5"><div><h2 className="font-extrabold">Latest Rate Comparison</h2><p className="text-xs muted" dir="rtl">مقارنة أحدث المعدلات</p></div>{comparisonSpec?<EconomicChart spec={comparisonSpec} height={320}/>:<div className="grid h-72 place-items-center text-sm muted">No comparable live rate indicators in this filter.</div>}</section>
      </div>}
      {data&&<div className="grid gap-4 xl:grid-cols-[1.35fr_.65fr]">
        <section className="glass-card p-5"><div className="flex items-center gap-3"><span className="icon-bubble"><Sparkles className="h-5 w-5"/></span><div><h2 className="font-extrabold">Data Insight Summary</h2><p className="text-xs muted" dir="rtl">ملخص الرؤى</p></div><span className="live-badge ms-auto">LIVE</span></div><p className="mt-4 text-sm leading-6 muted">{language==='ar'?data.summary.ar:data.summary.en}</p></section>
        <section className="glass-card p-5"><h2 className="font-extrabold">Sources</h2><p className="mt-1 text-xs muted">Trusted public-source registry</p><div className="mt-4"><SourceCards sources={(sources.data??[]).filter(s=>s.datasets?.some(d=>d.verification_status==='verified')).slice(0,4)} language={language}/></div></section>
      </div>}
    </div>
  </div>
}
