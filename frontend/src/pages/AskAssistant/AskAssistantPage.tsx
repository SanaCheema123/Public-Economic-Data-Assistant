import { ArrowRight, BarChart3, Bookmark, Bot, Download, Lightbulb, Send, ThumbsDown, ThumbsUp, TrendingUp } from 'lucide-react'
import { FormEvent, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { get, post, download, ApiError } from '../../api/client'
import type { ChatResponse } from '../../types/api'
import { PageHero } from '../../components/layout/PageHero'
import { EconomicChart } from '../../components/charts/EconomicChart'
import { CitationList } from '../../components/citations/CitationList'
import { SourceCards, type SourceCardData } from '../../components/sources/SourceCards'
import { useToast } from '../../components/ui/ToastProvider'

type ConversationMessage = { id:string; role:'user'|'assistant'; text:string; result?:ChatResponse; question?:string }

const prompts = [
  'Compare GDP growth and inflation over the last 5 years.',
  'Show the latest unemployment rate in Saudi Arabia.',
  'Show population growth over the last 5 years.',
  'Show female labor force participation over the last 5 years.'
]
const trending = [
  "What is Saudi Arabia's GDP growth rate in 2023?",
  'How has inflation changed in Saudi Arabia?',
  'What is the current unemployment rate?',
  'Show population growth over the last 5 years.',
]

export default function AskAssistantPage(){
  const {t,i18n}=useTranslation(); const language=i18n.language==='ar'?'ar':'en'
  const toast=useToast(); const [params,setParams]=useSearchParams(); const autoSent=useRef(false)
  const [input,setInput]=useState(''); const [busy,setBusy]=useState(false); const [sessionId,setSessionId]=useState<string|undefined>()
  const [messages,setMessages]=useState<ConversationMessage[]>([])
  const sources=useQuery({queryKey:['sources'],queryFn:()=>get<Array<SourceCardData & {source_type:string}>>('/api/sources')})

  const sendQuestion=async(question:string)=>{
    const clean=question.trim(); if(!clean||busy)return
    setMessages(m=>[...m,{id:`u-${Date.now()}`,role:'user',text:clean,question:clean}]); setInput(''); setBusy(true)
    try{
      const result=await post<ChatResponse>('/api/chat',{question:clean,language,chat_session_id:sessionId})
      setSessionId(result.chat_session_id)
      setMessages(m=>[...m,{id:`a-${result.result_id}`,role:'assistant',text:language==='ar'?result.answer_ar:result.answer,result,question:clean}])
    }catch(e){
      const msg=e instanceof ApiError?e.detail:t('networkError')
      setMessages(m=>[...m,{id:`e-${Date.now()}`,role:'assistant',text:msg}])
      toast.show(msg,'error')
    }finally{setBusy(false)}
  }

  useEffect(()=>{
    const q=params.get('q'); if(q&&!autoSent.current){autoSent.current=true; setParams({}, {replace:true}); void sendQuestion(q)}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[])

  const saveResult=async(result:ChatResponse,question:string)=>{
    try{await post('/api/saved',{query_result_id:result.result_id,item_type:'answer',title:question,description:language==='ar'?result.answer_ar:result.answer,payload:{chart:result.chart,data:result.data,verification_status:'verified'}});toast.show(t('savedDone'))}catch(e){toast.show(e instanceof ApiError?e.detail:'Unable to save','error')}
  }
  const saveChart=async(result:ChatResponse,question:string)=>{
    if(!result.chart)return
    try{await post('/api/saved',{query_result_id:result.result_id,item_type:'chart',title:`Chart — ${question}`,description:language==='ar'?(result.chart.title_ar||question):(result.chart.title||question),payload:{chart:result.chart,data:result.data,verification_status:'verified'}});toast.show('Chart saved')}catch(e){toast.show(e instanceof ApiError?e.detail:'Unable to save chart','error')}
  }
  const exportResult=async(result:ChatResponse,type:'pdf'|'csv')=>{
    try{await download(`/api/export/${type}`,{query_result_id:result.result_id,language},`economic-${result.result_id}.${type}`)}catch(e){toast.show(e instanceof ApiError?e.detail:'Export failed','error')}
  }
  const feedback=async(result:ChatResponse,rating:'helpful'|'not_helpful')=>{
    try{await post('/api/feedback',{query_result_id:result.result_id,rating});toast.show('Feedback recorded')}catch{toast.show('Could not record feedback','error')}
  }
  const submit=(e:FormEvent)=>{e.preventDefault();void sendQuestion(input)}

  return <div>
    <PageHero title={t('askTitle')} arabic={language==='en'?'اطرح سؤالك على المساعد الذكي':'Ask the Assistant'} description={t('askSub')}/>
    <div className="grid gap-4 p-4 md:p-6 lg:p-8 xl:grid-cols-[minmax(0,1fr)_390px]">
      <section className="glass-card flex min-h-[690px] flex-col overflow-hidden">
        <div className="flex-1 space-y-5 overflow-y-auto p-4 md:p-6 scrollbar-thin">
          {messages.length===0&&<div className="mx-auto grid max-w-2xl place-items-center py-24 text-center"><span className="icon-bubble !h-16 !w-16"><Bot className="h-7 w-7"/></span><h2 className="mt-5 text-2xl font-black">Ask about the available public-data catalog</h2><p className="mt-2 max-w-xl text-sm leading-6 muted">Questions are retrieved against registered indicators. Numeric answers are only returned when a dataset query succeeds and a source citation can be attached.</p><div className="mt-5 flex flex-wrap justify-center gap-2">{prompts.slice(0,3).map(p=><button key={p} onClick={()=>void sendQuestion(p)} className="rounded-full border bg-[#fbf7f3] px-4 py-2 text-xs font-semibold hover:bg-[#f4e9e1]" style={{borderColor:'var(--border)'}}>{p}</button>)}</div></div>}
          {messages.map(message=>message.role==='user'?<div key={message.id} className="ms-auto max-w-[82%] rounded-[22px] rounded-tr-md bg-[#efe2d9] px-5 py-4 text-sm leading-6">{message.text}</div>:<div key={message.id} className="flex gap-3"><span className="icon-bubble mt-1 shrink-0"><BarChart3 className="h-5 w-5"/></span><div className="min-w-0 flex-1"><div className="rounded-[24px] border bg-white/80 p-5" style={{borderColor:'var(--border)'}}>
            <div className="flex items-start justify-between gap-4"><p className="text-[15px] font-semibold leading-7">{message.text}</p>{message.result&&!message.result.unsupported&&<span className="live-badge shrink-0">VERIFIED</span>}</div>
            {message.result?.chart&&<div className="mt-5 rounded-2xl border bg-[#fbf8f4] p-3" style={{borderColor:'var(--border)'}}><div className="px-2 pt-1 text-sm font-extrabold">{language==='ar'?message.result.chart.title_ar:message.result.chart.title}</div><EconomicChart spec={message.result.chart} height={270}/></div>}
            {message.result&&<div className="mt-4"><CitationList citations={message.result.citations} language={language}/></div>}
            {message.result&&<div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-4" style={{borderColor:'var(--border)'}}><button onClick={()=>void feedback(message.result!,'helpful')} className="rounded-xl p-2 hover:bg-[#f5ece6]" aria-label="Helpful"><ThumbsUp className="h-4 w-4"/></button><button onClick={()=>void feedback(message.result!,'not_helpful')} className="rounded-xl p-2 hover:bg-[#f5ece6]" aria-label="Not helpful"><ThumbsDown className="h-4 w-4"/></button><button onClick={()=>void saveResult(message.result!,message.question||'Saved answer')} className="soft-button !px-3 !py-2 text-xs"><Bookmark className="h-4 w-4"/>{t('save')}</button>{message.result.chart&&<button onClick={()=>void saveChart(message.result!,message.question||'Saved chart')} className="soft-button !px-3 !py-2 text-xs"><BarChart3 className="h-4 w-4"/>Save chart</button>}<button onClick={()=>void exportResult(message.result!,'pdf')} className="soft-button !px-3 !py-2 text-xs"><Download className="h-4 w-4"/>{t('exportPdf')}</button><button onClick={()=>void exportResult(message.result!,'csv')} className="soft-button !px-3 !py-2 text-xs"><Download className="h-4 w-4"/>{t('exportCsv')}</button></div>}
          </div></div></div>)}
          {busy&&<div className="flex items-center gap-3"><span className="icon-bubble"><Bot className="h-5 w-5"/></span><div className="rounded-2xl border bg-white px-4 py-3 text-sm muted" style={{borderColor:'var(--border)'}}>Retrieving indicators, validating the query, and checking citations…</div></div>}
        </div>
        <form onSubmit={submit} className="border-t p-4" style={{borderColor:'var(--border)'}}><div className="flex items-center gap-2 rounded-full border bg-white p-2 ps-5 shadow-sm" style={{borderColor:'var(--border)'}}><input value={input} onChange={e=>setInput(e.target.value)} className="min-w-0 flex-1 bg-transparent text-sm outline-none" placeholder={t('askFollowup')} aria-label={t('askFollowup')}/><button disabled={busy||!input.trim()} className="grid h-11 w-11 place-items-center rounded-full bg-[#a98773] text-white disabled:opacity-40" aria-label="Send"><Send className="h-4 w-4 rtl:rotate-180"/></button></div></form>
      </section>

      <aside className="space-y-4">
        <section className="glass-card p-5"><div className="flex items-center gap-3"><span className="icon-bubble !h-10 !w-10"><Lightbulb className="h-4 w-4"/></span><h2 className="font-extrabold">{t('tryPrompts')}</h2></div><div className="mt-4 space-y-2">{prompts.map(p=><button key={p} onClick={()=>void sendQuestion(p)} className="flex w-full items-start gap-2 rounded-2xl border bg-white/55 p-3 text-start text-xs leading-5 transition hover:bg-[#fbf4ef]" style={{borderColor:'var(--border)'}}><ArrowRight className="mt-0.5 h-4 w-4 shrink-0 rtl:rotate-180"/>{p}</button>)}</div></section>
        <section className="glass-card p-5"><div className="flex items-center gap-3"><span className="icon-bubble !h-10 !w-10"><TrendingUp className="h-4 w-4"/></span><h2 className="font-extrabold">{t('trendingQuestions')}</h2></div><div className="mt-4 divide-y" style={{borderColor:'var(--border)'}}>{trending.map(p=><button key={p} onClick={()=>void sendQuestion(p)} className="flex w-full items-center gap-2 py-2.5 text-start text-xs leading-5 hover:text-[#7c5a47]"><ArrowRight className="h-3.5 w-3.5 shrink-0 rtl:rotate-180"/>{p}</button>)}</div></section>
        <section className="glass-card p-5"><h2 className="font-extrabold">{t('officialSources')}</h2><p className="mt-1 text-xs muted">Sources below have synchronized verified datasets available to the assistant.</p><div className="mt-4"><SourceCards sources={(sources.data??[]).filter(s=>s.datasets?.some(d=>d.verification_status==='verified')).slice(0,4)} language={language}/></div></section>
      </aside>
    </div>
  </div>
}
