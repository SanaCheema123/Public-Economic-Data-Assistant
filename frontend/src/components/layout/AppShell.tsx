import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const [open, setOpen] = useState(false)
  return <div className="min-h-screen app-grid-bg">
    <Sidebar open={open} onClose={()=>setOpen(false)}/>
    <Header onMenu={()=>setOpen(true)}/>
    <main className="min-h-screen pt-[72px] lg:ps-[292px]"><Outlet/></main>
  </div>
}
