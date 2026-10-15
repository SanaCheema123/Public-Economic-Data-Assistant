import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KPICard } from './KPICard'

describe('KPICard', () => {
  it('shows verified live status and value', () => {
    render(<KPICard language="en" item={{ indicator_id:'NY.GDP.MKTP.KD.ZG', name_en:'GDP Growth', name_ar:'الناتج المحلي', unit:'%', value:4.2, date:'2023-01-01', delta:.3, verification_status:'verified', series:[{date:'2022-01-01',value:3.9},{date:'2023-01-01',value:4.2}] }}/>)
    expect(screen.getByText('GDP Growth')).toBeInTheDocument()
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    expect(screen.getByText(/4\.2/)).toBeInTheDocument()
  })
})
