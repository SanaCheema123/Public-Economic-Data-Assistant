import { ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Brand } from '../../components/layout/Brand'
import { useAuth } from '../../services/auth'
import { ApiError } from '../../api/client'

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const from = (location.state as { from?: string } | null)?.from || '/app'

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await register(name, email, password)
      navigate(from, { replace: true })
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'Unable to complete authentication. Please try again.')
    } finally { setBusy(false) }
  }

  return <div className="grid min-h-screen bg-[#faf7f2] lg:grid-cols-[1fr_.9fr]">
    <section className="saudi-scene relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between lg:p-12">
      <Brand/>
      <div className="max-w-xl pb-8"><div className="inline-flex items-center gap-2 rounded-full border bg-white/55 px-4 py-2 text-xs font-bold" style={{borderColor:'var(--border)'}}><ShieldCheck className="h-4 w-4"/>Citation-first public data</div><h1 className="mt-5 text-5xl font-black leading-tight tracking-[-.04em]">Clear answers.<br/>Visible sources.<br/>Bilingual insight.</h1><p className="mt-5 max-w-lg text-base leading-7 muted">Ask questions about available Saudi economic and social datasets with live synchronized data, transparent provenance, and source citations.</p></div>
    </section>
    <section className="flex items-center justify-center p-5 sm:p-10"><div className="w-full max-w-md"><div className="mb-8 lg:hidden"><Brand/></div><p className="text-xs font-extrabold tracking-[.18em] text-[#9b7461]">PUBLIC ECONOMIC DATA ASSISTANT</p><h2 className="mt-3 text-4xl font-black tracking-tight">{mode==='login'?'Welcome back':'Create your account'}</h2><p className="mt-2 text-sm muted">{mode==='login'?'Sign in to continue to your research workspace.':'Register to save answers, export reports and manage your history.'}</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        {mode==='register' && <label className="block"><span className="mb-1.5 block text-sm font-bold">Full name</span><input required minLength={2} value={name} onChange={e=>setName(e.target.value)} className="h-12 w-full rounded-2xl border bg-white px-4 outline-none transition focus:border-[#b6947f]" style={{borderColor:'var(--border)'}} placeholder="Ahmed Alharbi"/></label>}
        <label className="block"><span className="mb-1.5 block text-sm font-bold">Email</span><input required type="email" value={email} onChange={e=>setEmail(e.target.value)} className="h-12 w-full rounded-2xl border bg-white px-4 outline-none transition focus:border-[#b6947f]" style={{borderColor:'var(--border)'}} placeholder="you@example.com"/></label>
        <label className="block"><span className="mb-1.5 block text-sm font-bold">Password</span><div className="relative"><input required minLength={8} type={show?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} className="h-12 w-full rounded-2xl border bg-white px-4 pe-12 outline-none transition focus:border-[#b6947f]" style={{borderColor:'var(--border)'}} placeholder="At least 8 characters"/><button type="button" onClick={()=>setShow(x=>!x)} className="absolute end-3 top-1/2 -translate-y-1/2 rounded-lg p-2" aria-label={show?'Hide password':'Show password'}>{show?<EyeOff className="h-4 w-4"/>:<Eye className="h-4 w-4"/>}</button></div></label>
        {error && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
        <button disabled={busy} className="primary-button !h-12 w-full disabled:opacity-50">{busy?'Please wait…':mode==='login'?'Sign In':'Create Account'}<ArrowRight className="h-4 w-4 rtl:rotate-180"/></button>
      </form>
      <p className="mt-6 text-center text-sm muted">{mode==='login'?'New here?':'Already have an account?'} <Link className="font-bold text-[#7c5a47]" to={mode==='login'?'/register':'/login'}>{mode==='login'?'Create an account':'Sign in'}</Link></p>
      <Link to="/" className="mt-6 block text-center text-xs font-semibold text-[#8b776a]">← Back to landing page</Link>
    </div></section>
  </div>
}
