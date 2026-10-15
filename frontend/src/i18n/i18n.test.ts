import { describe, expect, it } from 'vitest'
import i18n, { applyLanguage } from './index'

describe('language switching', () => {
  it('switches to Arabic and enables RTL', async () => {
    applyLanguage('ar')
    expect(i18n.language).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
    applyLanguage('en')
    expect(document.documentElement.dir).toBe('ltr')
  })
})
