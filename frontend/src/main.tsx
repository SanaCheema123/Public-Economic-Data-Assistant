import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, Navigate, RouterProvider, useLocation } from 'react-router-dom'
import './i18n'
import './styles/index.css'
import LandingPage from './pages/Landing/LandingPage'
import HomePage from './pages/Home/HomePage'
import AskAssistantPage from './pages/AskAssistant/AskAssistantPage'
import InsightsPage from './pages/Insights/InsightsPage'
import SavedItemsPage from './pages/SavedItems/SavedItemsPage'
import SettingsPage from './pages/Settings/SettingsPage'
import { AuthPage } from './pages/Auth/AuthPage'
import { AppShell } from './components/layout/AppShell'
import { AuthProvider, useAuth } from './services/auth'
import { ToastProvider } from './components/ui/ToastProvider'
import { LoadingCard } from './components/ui/AsyncState'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 15_000, refetchOnWindowFocus: false } }
})

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth(); const location = useLocation()
  if (loading) return <div className="grid min-h-screen place-items-center bg-[#faf7f2] p-6"><div className="w-full max-w-lg"><LoadingCard label="Opening your data workspace…"/></div></div>
  if (!user) return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />
  return children
}

function NotFound(){return <div className="grid min-h-screen place-items-center bg-[#faf7f2] p-6 text-center"><div><div className="text-7xl font-black text-[#d7bdb0]">404</div><h1 className="mt-3 text-2xl font-black">Page not found</h1><a href="/" className="primary-button mt-5">Return home</a></div></div>}

const router=createBrowserRouter([
  {path:'/',element:<LandingPage/>},
  {path:'/login',element:<AuthPage mode="login"/>},
  {path:'/register',element:<AuthPage mode="register"/>},
  {path:'/app',element:<Protected><AppShell/></Protected>,children:[
    {index:true,element:<HomePage/>},
    {path:'ask',element:<AskAssistantPage/>},
    {path:'insights',element:<InsightsPage/>},
    {path:'saved',element:<SavedItemsPage/>},
    {path:'settings',element:<SettingsPage/>},
  ]},
  {path:'*',element:<NotFound/>}
])

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><AuthProvider><ToastProvider><RouterProvider router={router}/></ToastProvider></AuthProvider></QueryClientProvider></React.StrictMode>)
