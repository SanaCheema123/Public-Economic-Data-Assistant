import { ArrowRight, BarChart3, BookOpenText, CalendarDays, ChartNoAxesCombined, CheckCircle2, FileDown, Globe2, Languages, Link2, MessageSquareText, Play, Search, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { applyLanguage } from '../../i18n'
import { Brand } from '../../components/layout/Brand'

const features = [
  { icon: MessageSquareText, en:'Arabic and English conversations', ar:'محادثات بالعربية والإنجليزية', text:'Ask naturally in your preferred language.' },
  { icon: Link2, en:'Source-linked answers', ar:'إجابات مرتبطة بالمصادر', text:'Every factual response can show its provenance.' },
  { icon: ChartNoAxesCombined, en:'Automatic charts and summaries', ar:'رسوم وملخصات تلقائية', text:'Turn query results into clear visual insight.' },
  { icon: BookOpenText, en:'Indicator definitions', ar:'تعريفات المؤشرات', text:'Understand what each indicator means.' },
  { icon: CalendarDays, en:'Dataset and date citations', ar:'توثيق مجموعة البيانات والتاريخ', text:'See the dataset, period and verification status.' },
  { icon: Search, en:'Natural language questions', ar:'أسئلة باللغة الطبيعية', text:'Move from a question to a safe database query.' },
  { icon: FileDown, en:'PDF and CSV export', ar:'تصدير PDF وCSV', text:'Download research-ready results.' },
]

function HeroPreview() {
  return <div className="relative w-full max-w-[620px] rounded-[30px] border border-white/80 bg-white/80 p-4 shadow-soft backdrop-blur-md">
    <div className="flex items-center justify-between border-b pb-3" style={{borderColor:'var(--border)'}}><Brand/><span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">● Online</span></div>
    <div className="mt-4 grid grid-cols-[116px_1fr] gap-4">
      <div className="space-y-2"><div className="rounded-xl bg-[#f0e3da] px-3 py-2 text-xs font-bold">+ New Chat</div>{['Home','Saved','History','Favorites'].map((x,i)=><div key={x} className={`rounded-xl px-3 py-2 text-xs ${i===0?'bg-[#f8f1ec] font-bold':''}`}>{x}</div>)}</div>
      <div className="min-w-0"><div className="ms-auto max-w-[78%] rounded-2xl rounded-tr-md bg-[#f1e7df] p-3 text-end text-xs" dir="rtl">ما هو معدل نمو الناتج المحلي الإجمالي في السعودية؟</div>
        <div className="mt-3 rounded-2xl border bg-white p-4" style={{borderColor:'var(--border)'}}><div className="flex gap-3"><span className="icon-bubble !h-10 !w-10"><BarChart3 className="h-4 w-4"/></span><div><div className="text-xs font-bold">GDP growth result</div><p className="mt-1 text-[11px] leading-relaxed muted">Results are generated from available data with a visible source status.</p></div></div>
          <div className="mt-4 flex h-28 items-end gap-3 border-b border-s-0 px-4 pb-0" style={{borderColor:'#eadfd8'}}>{[18,44,38,76,56].map((h,i)=><div key={i} className="flex-1 rounded-t-md bg-[#c6a894]" style={{height:`${h}%`}}><span className="sr-only">bar</span></div>)}</div>
          <div className="mt-3 flex items-center justify-between rounded-xl bg-[#fbf7f3] px-3 py-2"><span className="text-[10px] muted">Source & citation shown with each answer</span><ShieldCheck className="h-4 w-4 text-[#7c5a47]"/></div>
        </div>
        <div className="mt-3 rounded-full border bg-white px-4 py-2 text-xs muted" style={{borderColor:'var(--border)'}}>Ask a question in Arabic or English...</div>
      </div>
    </div>
  </div>
}

export default function LandingPage(){
  const { t, i18n }=useTranslation(); const isArabic=i18n.language==='ar'
  return <div className="min-h-screen bg-[#faf7f2]">
    <header className="fixed inset-x-0 top-0 z-50 border-b bg-[#fcfaf7]/90 backdrop-blur-xl" style={{borderColor:'var(--border)'}}><div className="mx-auto flex h-[72px] max-w-[1460px] items-center gap-8 px-5 lg:px-10"><Brand/><nav className="mx-auto hidden items-center gap-8 text-sm font-semibold lg:flex"><a href="#home">Home</a><a href="#features">Features</a><a href="#about">About</a><a href="#contact">Contact</a></nav><div className="ms-auto flex items-center gap-2"><div className="hidden rounded-full border p-1 sm:flex" style={{borderColor:'var(--border)'}}><button onClick={()=>applyLanguage('en')} className={`rounded-full px-2.5 py-1 text-xs font-bold ${!isArabic?'bg-[#efe1d7]':''}`}>EN</button><button onClick={()=>applyLanguage('ar')} className={`rounded-full px-2.5 py-1 text-xs font-bold ${isArabic?'bg-[#efe1d7]':''}`}>عربي</button></div><Link to="/login" className="soft-button !px-5 !py-2.5">{t('signIn')}</Link><Link to="/app" className="primary-button hidden !px-5 !py-2.5 sm:inline-flex">{t('tryItNow')}<ArrowRight className="h-4 w-4 rtl:rotate-180"/></Link></div></div></header>

    <main id="home" className="pt-[72px]">
      <section className="saudi-scene relative overflow-hidden border-b" style={{borderColor:'var(--border)'}}><div className="mx-auto grid max-w-[1460px] items-center gap-10 px-5 py-12 lg:grid-cols-[.9fr_1.1fr] lg:px-10 lg:py-16"><div className="relative z-10"><p className="text-xs font-extrabold tracking-[.18em] text-[#9b7461]">{t('heroKicker')}</p><h1 className="mt-4 text-4xl font-black leading-[1.02] tracking-[-.04em] sm:text-5xl lg:text-[60px]"><span className="block">{t('heroTitle1')}</span><span className="block">{t('heroTitle2')}</span></h1><div className="mt-4 text-xl font-semibold text-[#6f4a38]" dir={isArabic?'rtl':'ltr'}>{t('heroArabic')}</div><p className="mt-5 max-w-xl text-[15px] leading-7 muted">{t('heroDescription')}</p><div className="mt-7 flex flex-wrap gap-3"><Link to="/app" className="primary-button">{t('startExploring')}<ArrowRight className="h-4 w-4 rtl:rotate-180"/></Link><a href="#features" className="soft-button"><Play className="h-4 w-4 fill-current"/>{t('seeDemo')}</a></div><div className="mt-9 flex flex-wrap gap-x-8 gap-y-4 text-sm"><div className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-[#7c5a47]"/><span><strong>{t('trustedData')}</strong><small className="block muted">with verification labels</small></span></div><div className="flex items-center gap-2"><Globe2 className="h-5 w-5 text-[#7c5a47]"/><span><strong>{t('bilingual')}</strong><small className="block muted">Arabic & English</small></span></div><div className="flex items-center gap-2"><CheckCircle2 className="h-5 w-5 text-[#7c5a47]"/><span><strong>{t('citedAnswers')}</strong><small className="block muted">with provenance</small></span></div></div></div><div className="relative z-10 flex justify-center lg:justify-end"><HeroPreview/></div></div></section>

      <section id="features" className="mx-auto max-w-[1460px] px-5 py-12 lg:px-10"><div className="flex items-end justify-between gap-4"><div><h2 className="section-title">{t('featureTitle')}</h2><p className="mt-1 text-sm muted">{t('featureSub')}</p></div><a href="#about" className="hidden text-sm font-semibold text-[#805d49] md:block">Explore all features →</a></div><div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">{features.map(({icon:Icon,en,ar:arLabel,text})=><div key={en} className="glass-card min-h-[148px] p-4"><span className="icon-bubble"><Icon className="h-5 w-5"/></span><h3 className="mt-3 text-sm font-extrabold leading-tight">{isArabic?arLabel:en}</h3><p className="mt-2 text-xs leading-relaxed muted">{text}</p></div>)}</div></section>

      <section id="about" className="mx-auto max-w-[1460px] px-5 pb-10 lg:px-10"><div className="grid gap-3 rounded-3xl border bg-white/55 p-5 text-sm md:grid-cols-4" style={{borderColor:'var(--border)'}}>{[[Languages,'For citizens, students, researchers and journalists'],[BarChart3,'Make public data more accessible'],[ShieldCheck,'Citation-first and unsupported-answer protection'],[BookOpenText,'Data for a brighter tomorrow']].map(([Icon,text]:any)=><div className="flex items-center gap-3" key={text}><Icon className="h-5 w-5 text-[#9b7461]"/><span>{text}</span></div>)}</div></section>

      <section id="contact" className="mx-auto max-w-[1460px] px-5 pb-8 lg:px-10"><div className="saudi-scene overflow-hidden rounded-[28px] border px-7 py-7 md:flex md:items-center md:justify-between" style={{borderColor:'var(--border)'}}><div><h2 className="text-2xl font-black">{t('ctaTitle')}</h2><p className="mt-1 text-sm muted">{t('ctaSub')}</p></div><Link to="/register" className="primary-button mt-5 md:mt-0">{t('tryItNow')}<ArrowRight className="h-4 w-4 rtl:rotate-180"/></Link></div></section>
    </main>
    <footer className="border-t bg-[#fcfaf7]" style={{borderColor:'var(--border)'}}><div className="mx-auto flex max-w-[1460px] flex-col gap-5 px-5 py-7 text-xs md:flex-row md:items-center lg:px-10"><Brand/><div className="md:ms-auto flex gap-5 muted"><a href="#home">Home</a><a href="#features">Features</a><a href="#about">About</a><a href="#contact">Contact</a></div><div className="muted">© 2026 Public Economic Data Assistant.</div></div></footer>
  </div>
}
