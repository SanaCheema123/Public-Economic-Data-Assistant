export type User = {
  id: string
  full_name: string
  email: string
  preferred_language: 'en' | 'ar'
  theme_preference: string
  notification_preference: boolean
  ai_preference?: string | null
}

export type Citation = {
  id?: string | null
  title: string
  source_name: string
  source_name_ar?: string | null
  dataset_name: string
  dataset_name_ar?: string | null
  indicator_name?: string | null
  indicator_name_ar?: string | null
  period?: string | null
  url: string
  verification_status: string
}

export type ChartSpec = {
  type: 'line' | 'bar' | 'area' | 'pie' | 'donut' | 'grouped_bar'
  title: string
  title_ar: string
  x: Array<string | number>
  y: number[]
  series: Array<{ name: string; x: Array<string | number>; y: number[] }>
  labels: string[]
  values: number[]
  x_label?: string | null
  y_label?: string | null
}

export type ChatResponse = {
  query_id: string
  chat_session_id: string
  result_id: string
  answer: string
  answer_ar: string
  language: 'en' | 'ar'
  indicator?: {
    id: string
    indicator_id: string
    name: string
    name_ar: string
    unit: string
    category: string
    description?: string
    description_ar?: string
    verification_status: string
  } | null
  data: Array<Record<string, unknown>>
  chart?: ChartSpec | null
  citations: Citation[]
  sources: Array<Record<string, unknown>>
  confidence: 'high' | 'medium' | 'low' | 'unsupported'
  unsupported: boolean
  generated_at: string
  sql_preview?: string | null
}

export type DashboardPayload = {
  kpis: Array<{
    id: string; indicator_id: string; name_en: string; name_ar: string; unit: string; category: string
    verification_status: string; value: number; date: string; period_label?: string; delta?: number | null
    series: Array<{ date: string; value: number }>
    source?: { id?: string | null; slug?: string | null; name_en?: string | null; name_ar?: string | null; url?: string | null; official?: boolean; last_sync?: string | null }
  }>
  trends: DashboardPayload['kpis']
  recent_questions: Array<{ id: string; question: string; language: string; created_at: string }>
  summary: { en: string; ar: string; live: boolean; periods?: string[] }
  data_status: { mode:string; provider:string; verified_indicators:number; verified_values:number; latest_observation_date?:string|null; last_synchronization_date?:string|null; refresh_hours:number; gastat_refresh_minutes?:number; official_headlines_ready?:boolean; gastat_headlines?:number; world_bank_indicators?:number; ready:boolean; sources?:Record<string,{ready:boolean;last_sync?:string|null;official?:boolean;last_error?:string|null}> }
  sources: Array<{ id: string; name_en: string; name_ar: string; url: string; slug: string; source_type?: string }>
}

export type InsightsPayload = {
  cards: Array<{ id: string; indicator_id: string; name_en: string; name_ar: string; unit: string; value: number; date: string; period_label?:string; category: string; verification_status: string; source?:{name_en?:string|null;name_ar?:string|null;url?:string|null;official?:boolean} }>
  series: Array<{ id: string; indicator_id: string; name_en: string; name_ar: string; unit: string; values: Array<{ date: string; value: number; region?: string | null; sector?: string | null }> }>
  live: boolean
  data_status: { mode:string; provider:string; verified_indicators:number; verified_values:number; latest_observation_date?:string|null; last_synchronization_date?:string|null; refresh_hours:number; gastat_refresh_minutes?:number; official_headlines_ready?:boolean; gastat_headlines?:number; world_bank_indicators?:number; ready:boolean; sources?:Record<string,{ready:boolean;last_sync?:string|null;official?:boolean;last_error?:string|null}> }
  summary: { en:string; ar:string }
}

export type SavedPayload = {
  items: Array<{ id: string; query_result_id?: string | null; collection_id?: string | null; item_type: string; title: string; description?: string | null; payload: Record<string, unknown>; created_at: string; updated_at: string }>
  collections: Array<{ id: string; name: string; description?: string | null; created_at: string }>
}
