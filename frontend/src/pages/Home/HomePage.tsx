import { ArrowRight, MessageSquare, Sparkles, Wifi } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { get } from '../../api/client'
import type { ChartSpec, DashboardPayload } from '../../types/api'
import { useAuth } from '../../services/auth'
import { PageHero } from '../../components/layout/PageHero'
import { KPICard } from '../../components/cards/KPICard'
import { EconomicChart } from '../../components/charts/EconomicChart'
import { SourceCards } from '../../components/sources/SourceCards'
import { ErrorCard, Skeleton } from '../../components/ui/AsyncState'
import { relativeTime } from '../../utils/format'

export default function HomePage() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const language = i18n.language === 'ar' ? 'ar' : 'en'
  const query = useQuery({ queryKey: ['dashboard'], queryFn: () => get<DashboardPayload>('/api/dashboard'), refetchInterval: 5 * 60 * 1000 })
  const data = query.data
  const chart: ChartSpec | null = data && data.trends.length ? {
    type: 'grouped_bar', title: t('economicTrends'), title_ar: 'الاتجاهات الاقتصادية', x: [], y: [], labels: [], values: [],
    series: data.trends.map(item => ({ name: language==='ar'?item.name_ar:item.name_en, x: item.series.map(x=>x.date.slice(0,4)), y: item.series.map(x=>x.value) })),
    x_label: language==='ar'?'السنة':'Year', y_label:'%'
  } : null
  const firstName = user?.full_name?.split(' ')[0] || 'User'
  return <div>
    <PageHero title={t('welcome',{name:firstName})} arabic={language==='en'?'مرحباً بك مجدداً':''} description={t('dashboardSub')}>
      <div className="rounded-2xl border bg-white/50 px-4 py-3 text-end text-xs" style={{borderColor:'var(--border)'}}><div className="font-bold">{new Intl.DateTimeFormat(language==='ar'?'ar-SA':'en-GB',{dateStyle:'full'}).format(new Date())}</div><div className="mt-1 muted">Knowledge drives progress</div></div>
    </PageHero>
    <div className="space-y-4 p-4 md:p-6 lg:p-8">
      {query.isError && <ErrorCard message="Live dashboard data could not be loaded. Check the backend and data-source connection." action={<button className="soft-button" onClick={()=>query.refetch()}>Retry</button>}/>} 
      {data && !data.data_status.ready && <ErrorCard message={language==='ar'?'لا توجد بيانات حية متزامنة حالياً. شغّل مزامنة البيانات من الخادم.':'No synchronized live observations are available yet. Run the backend live-data sync and retry.'}/>} 
      {data?.data_status.ready && data.data_status.official_headlines_ready === false && <ErrorCard message={language==='ar'?'تعذر تحديث المؤشرات الرسمية المباشرة من الهيئة العامة للإحصاء؛ يتم عرض بيانات البنك الدولي الحية مؤقتاً مع إظهار المصدر على كل بطاقة.':'GASTAT official headline refresh is temporarily unavailable; verified live World Bank data is being used as a fallback and every card shows its source.'}/>} 
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {query.isLoading ? Array.from({length:4}).map((_,i)=><Skeleton key={i} className="h-[172px]"/>) : data?.kpis.map(item=><KPICard key={item.id} item={item} language={language}/>) }
      </section>
      {data && <div className="grid gap-4 xl:grid-cols-[1.08fr_.92fr]">
        <section className="glass-card overflow-hidden p-5"><div className="flex items-center justify-between"><div><h2 className="text-lg font-extrabold">{t('economicTrends')}</h2><p className="text-xs muted">{language==='ar'?'سلاسل زمنية موثوقة ومتزامنة من المصدر العام':'Verified time series synchronized from the public source'}</p></div><span className="live-badge"><Wifi className="h-3 w-3"/> LIVE</span></div>{chart?<EconomicChart spec={chart} height={280}/>:<div className="grid h-64 place-items-center text-sm muted">No synchronized trend data yet.</div>}</section>
        <section className="glass-card p-5"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><span className="icon-bubble !h-10 !w-10"><MessageSquare className="h-4 w-4"/></span><h2 className="text-lg font-extrabold">{t('recentQuestions')}</h2></div><Link to="/app/ask" className="text-xs font-bold text-[#805d49]">View all →</Link></div><div className="mt-4 space-y-2">{data.recent_questions.length===0?<div className="rounded-2xl bg-[#fbf8f4] p-6 text-center text-sm muted">Ask your first question and it will appear here.</div>:data.recent_questions.map(q=><Link key={q.id} to={`/app/ask?q=${encodeURIComponent(q.question)}`} className="flex items-center justify-between gap-3 rounded-2xl border bg-white/60 px-4 py-3 text-sm transition hover:bg-[#fbf5f0]" style={{borderColor:'var(--border)'}}><span className="line-clamp-1">{q.question}</span><small className="shrink-0 muted">{relativeTime(q.created_at,language)}</small></Link>)}</div></section>
      </div>}
      {data && <div className="grid gap-4 xl:grid-cols-[1.08fr_.92fr]">
        <section className="glass-card p-5"><div className="flex items-center gap-3"><span className="icon-bubble"><Sparkles className="h-5 w-5"/></span><div><h2 className="text-lg font-extrabold">{t('aiSummary')}</h2><p className="text-xs muted">{language==='ar'?'ملخص قائم على البيانات المتزامنة':'Grounded summary of synchronized data'}</p></div><span className="live-badge ms-auto">VERIFIED</span></div><p className="mt-4 max-w-4xl text-sm leading-6 muted">{language==='ar'?data.summary.ar:data.summary.en}</p><div className="mt-4"><Link to="/app/insights" className="soft-button !py-2.5">Explore in detail <ArrowRight className="h-4 w-4 rtl:rotate-180"/></Link></div></section>
        <section className="glass-card p-5"><div className="flex items-center justify-between"><h2 className="text-lg font-extrabold">{t('verifiedSources')}</h2><span className="text-[11px] muted">{data.data_status.last_synchronization_date?`Synced ${new Date(data.data_status.last_synchronization_date).toLocaleString()}`:'Awaiting sync'}</span></div><div className="mt-4"><SourceCards sources={data.sources} language={language}/></div></section>
      </div>}
    </div>
  </div>
}
