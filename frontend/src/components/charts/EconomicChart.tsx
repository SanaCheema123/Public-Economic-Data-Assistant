import { lazy, Suspense, useMemo } from 'react'
import type { ChartSpec } from '../../types/api'
import { useTranslation } from 'react-i18next'

const Plot = lazy(() => import('react-plotly.js'))

const palette = ['#a98773', '#d7bdb0', '#d6ccc2', '#7f6658', '#b9a89d', '#e3d5ca']

export function EconomicChart({ spec, height = 300, showLegend = true }: { spec: ChartSpec; height?: number; showLegend?: boolean }) {
  const { i18n } = useTranslation()
  const ar = i18n.language === 'ar'
  const data = useMemo<any[]>(() => {
    if (spec.type === 'donut' || spec.type === 'pie') {
      return [{ type: 'pie', labels: spec.labels, values: spec.values, hole: spec.type === 'donut' ? .62 : 0, marker: { colors: palette }, textinfo: 'percent', hovertemplate: '%{label}<br>%{value}<extra></extra>' }]
    }
    if (spec.type === 'grouped_bar') {
      return spec.series.map((series, idx) => ({ type: 'bar', name: series.name, x: series.x, y: series.y, marker: { color: palette[idx % palette.length] }, hovertemplate: '%{x}<br>%{y}<extra>%{fullData.name}</extra>' }))
    }
    const mode = spec.type === 'bar' ? undefined : 'lines+markers'
    return [{
      type: spec.type === 'bar' ? 'bar' : 'scatter', mode, x: spec.x, y: spec.y,
      fill: spec.type === 'area' ? 'tozeroy' : undefined,
      line: { color: palette[0], width: 3, shape: 'spline' }, marker: { color: palette[0], size: 7 },
      hovertemplate: '%{x}<br>%{y}<extra></extra>'
    }]
  }, [spec])
  return <div className="plot-container w-full" dir={ar ? 'rtl' : 'ltr'}>
    <Suspense fallback={<div className="grid place-items-center" style={{height}}><span className="text-sm muted">Loading chart…</span></div>}>
      <Plot
        data={data}
        layout={{
          autosize: true, height, margin: { l: 48, r: 18, t: 14, b: 42 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
          font: { family: ar ? 'Tahoma, Arial, sans-serif' : 'Inter, Arial, sans-serif', color: '#514b48', size: 12 },
          xaxis: { gridcolor: 'rgba(124,90,71,.07)', zerolinecolor: 'rgba(124,90,71,.1)', title: { text: spec.x_label || '' }, automargin: true },
          yaxis: { gridcolor: 'rgba(124,90,71,.09)', zerolinecolor: 'rgba(124,90,71,.12)', title: { text: spec.y_label || '' }, automargin: true },
          legend: { orientation: 'h', x: 0, y: 1.14 }, showlegend: showLegend && (spec.series?.length > 1 || spec.type === 'donut' || spec.type === 'pie'),
          barmode: spec.type === 'grouped_bar' ? 'group' : undefined,
          hoverlabel: { bgcolor: '#fffaf6', bordercolor: '#d7bdb0', font: { color: '#1e2530' } }
        }}
        config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d','select2d','autoScale2d'] }}
        style={{ width: '100%', height }}
        useResizeHandler
      />
    </Suspense>
  </div>
}

export function Sparkline({ values, positive = true }: { values: number[]; positive?: boolean }) {
  if (!values.length) return null
  const width = 130, height = 42, pad = 3
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1
  const points = values.map((v,i)=>`${pad + (width-2*pad)*(i/Math.max(1,values.length-1))},${height-pad-(height-2*pad)*((v-min)/span)}`).join(' ')
  return <svg viewBox={`0 0 ${width} ${height}`} className="h-10 w-32" aria-hidden="true"><polyline points={points} fill="none" stroke={positive ? '#6f9f7f' : '#c97873'} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
