import { useState, useEffect } from 'react'
import {
  BarChart3, AlertTriangle, CheckCircle, Search, Download, Loader2,
  AlertCircle, TrendingUp, Check, Sparkles, Layers, Globe, Filter,
  ChevronDown, ChevronUp, ChevronRight, ArrowRight, EyeOff, RotateCcw
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

function CoherenceModule() {
  const [analyzing, setAnalyzing] = useState(false)
  const [message, setMessage] = useState(null)
  const [tolerancePercent, setTolerancePercent] = useState(15)
  const [referenceMarket, setReferenceMarket] = useState('France')
  const [targetMarket, setTargetMarket] = useState('')
  const [availableMarkets, setAvailableMarkets] = useState([])
  const [analysisTypes, setAnalysisTypes] = useState(['intra_product', 'cross_market'])
  const [analysis, setAnalysis] = useState(null)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [marketFilter, setMarketFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('severity')
  const [selectedAnomalies, setSelectedAnomalies] = useState(new Set())
  const [applying, setApplying] = useState(false)
  const [dismissing, setDismissing] = useState(false)
  const [showAiSummary, setShowAiSummary] = useState(true)
  const [expandedRows, setExpandedRows] = useState(new Set())
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 50

  useEffect(() => { loadMarkets() }, [])

  const loadMarkets = async () => {
    try {
      const r = await axios.get(`${API_URL}/coherence/markets`)
      setAvailableMarkets(r.data.markets || [])
    } catch (e) {
      try {
        const r = await axios.get(`${API_URL}/pricing/coherence/markets`)
        setAvailableMarkets(r.data.markets || [])
      } catch (e2) { console.error('Error loading markets:', e2) }
    }
  }

  const runAnalysis = async () => {
    try {
      setAnalyzing(true); setMessage(null); setAnalysis(null); setSelectedAnomalies(new Set()); setExpandedRows(new Set()); setPage(1)
      const r = await axios.post(`${API_URL}/coherence/analyze`, {
        tolerance_percent: tolerancePercent, reference_market: referenceMarket,
        target_market: targetMarket || null, analysis_types: analysisTypes
      })
      setAnalysis(r.data)
      if (r.data.stats.total_anomalies === 0) setMessage({ type: 'success', text: 'Aucune anomalie ! Les prix sont cohérents.' })
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || e.message })
    } finally { setAnalyzing(false) }
  }

  const filteredAnomalies = (analysis?.anomalies || []).filter(a => {
    if (severityFilter !== 'all' && a.severity !== severityFilter) return false
    if (typeFilter !== 'all' && a.type !== typeFilter) return false
    if (marketFilter !== 'all' && a.market !== marketFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      if (!(a.product_title || '').toLowerCase().includes(q) && !(a.variant_title || '').toLowerCase().includes(q)) return false
    }
    return true
  }).sort((a, b) => {
    const sev = { critical: 3, warning: 2, minor: 1 }
    if (sortBy === 'severity') return (sev[b.severity] || 0) - (sev[a.severity] || 0) || b.deviation_percent - a.deviation_percent
    if (sortBy === 'deviation') return b.deviation_percent - a.deviation_percent
    if (sortBy === 'product') return (a.product_title || '').localeCompare(b.product_title || '')
    return 0
  })

  const paginatedAnomalies = filteredAnomalies.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const totalPages = Math.ceil(filteredAnomalies.length / PAGE_SIZE)
  const anomalyMarkets = [...new Set((analysis?.anomalies || []).map(a => a.market))].sort()

  const toggleSelect = (key) => { const s = new Set(selectedAnomalies); s.has(key) ? s.delete(key) : s.add(key); setSelectedAnomalies(s) }
  const selectAllFiltered = () => { const s = new Set(selectedAnomalies); filteredAnomalies.forEach(a => s.add(`${a.variant_id}-${a.market}`)); setSelectedAnomalies(s) }
  const deselectAll = () => setSelectedAnomalies(new Set())
  const toggleExpand = (key) => { const s = new Set(expandedRows); s.has(key) ? s.delete(key) : s.add(key); setExpandedRows(s) }

  const applyCorrections = async () => {
    if (selectedAnomalies.size === 0) return
    const corrections = (analysis?.anomalies || []).filter(a => selectedAnomalies.has(`${a.variant_id}-${a.market}`)).map(a => ({ variant_id: a.variant_id, market: a.market, suggested_price: a.suggested_price, currency: a.currency }))
    if (!window.confirm(`Corriger ${corrections.length} prix ?`)) return
    try {
      setApplying(true)
      const r = await axios.post(`${API_URL}/coherence/apply`, { corrections, dry_run: false })
      if (r.data.applied) { setMessage({ type: 'success', text: `${r.data.results.updated_count} prix corrigés !` }); setSelectedAnomalies(new Set()); setTimeout(() => runAnalysis(), 1500) }
    } catch (e) { setMessage({ type: 'error', text: e.response?.data?.detail || e.message }) }
    finally { setApplying(false) }
  }

  const dismissAnomalies = async () => {
    if (selectedAnomalies.size === 0) return
    const keys = (analysis?.anomalies || [])
      .filter(a => selectedAnomalies.has(`${a.variant_id}-${a.market}`))
      .map(a => `${a.variant_id}:${a.market}`)
    if (!window.confirm(`Ignorer ${keys.length} anomalies ? Elles n'apparaîtront plus aux prochaines analyses.`)) return
    try {
      setDismissing(true)
      await axios.post(`${API_URL}/coherence/dismiss`, { keys })
      // Retirer les dismissed de l'analyse locale
      const dismissedSet = new Set(keys)
      const remaining = analysis.anomalies.filter(a => !dismissedSet.has(`${a.variant_id}:${a.market}`))
      setAnalysis({ ...analysis, anomalies: remaining, stats: { ...analysis.stats, total_anomalies: remaining.length, dismissed_count: (analysis.stats.dismissed_count || 0) + keys.length } })
      setSelectedAnomalies(new Set())
      setMessage({ type: 'success', text: `${keys.length} anomalies ignorées.` })
    } catch (e) { setMessage({ type: 'error', text: e.response?.data?.detail || e.message }) }
    finally { setDismissing(false) }
  }

  const exportCSV = () => {
    if (!filteredAnomalies.length) return
    const h = ['Type', 'Sévérité', 'Produit', 'Variante', 'Comparé à', 'Marché', 'Devise', 'Prix actuel', 'Prix variante précédente', 'Écart %', 'Description']
    const rows = filteredAnomalies.map(a => [a.type === 'intra_product' ? 'Intra-produit' : 'Cross-marché', a.severity, a.product_title || '', a.variant_title || '', a.reference_variant_title || '', a.market, a.currency || '', a.current_price, a.reference_price || '', `${a.deviation_percent}%`, a.description || ''])
    const BOM = '\uFEFF'
    const csv = BOM + [h, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `coherence_${new Date().toISOString().split('T')[0]}.csv`; link.click()
  }

  const getSeverityStyle = (s) => s === 'critical' ? 'bg-red-100 text-red-700' : s === 'warning' ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'

  return (
    <div className="max-w-[1400px]">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <BarChart3 className="w-7 h-7 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Analyse de Cohérence</h1>
        </div>
        <p className="text-gray-500">Détectez les incohérences de prix entre vos marchés et au sein de vos produits</p>
      </div>

      {/* Paramètres */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2"><Filter className="w-4 h-4" /> Paramètres</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Marché de référence</label>
            <select value={referenceMarket} onChange={e => setReferenceMarket(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              {availableMarkets.map(m => <option key={m.name || m} value={m.name || m}>{m.name || m} ({m.currency || 'EUR'})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Marché à analyser</label>
            <select value={targetMarket} onChange={e => setTargetMarket(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="">Marché de référence</option>
              {availableMarkets.filter(m => (m.name || m) !== referenceMarket).map(m => <option key={m.name || m} value={m.name || m}>{m.name || m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tolérance (%)</label>
            <input type="number" value={tolerancePercent} onChange={e => setTolerancePercent(parseFloat(e.target.value) || 0)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" min={1} max={100} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Types d'analyse</label>
            <div className="flex flex-col gap-1.5 mt-1">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={analysisTypes.includes('intra_product')} onChange={e => e.target.checked ? setAnalysisTypes([...analysisTypes, 'intra_product']) : setAnalysisTypes(analysisTypes.filter(t => t !== 'intra_product'))} className="rounded border-gray-300" />
                <Layers className="w-3.5 h-3.5 text-purple-500" /> Intra-produit
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={analysisTypes.includes('cross_market')} onChange={e => e.target.checked ? setAnalysisTypes([...analysisTypes, 'cross_market']) : setAnalysisTypes(analysisTypes.filter(t => t !== 'cross_market'))} className="rounded border-gray-300" />
                <Globe className="w-3.5 h-3.5 text-blue-500" /> Cross-marchés
              </label>
            </div>
          </div>
        </div>
        <button onClick={runAnalysis} disabled={analyzing || analysisTypes.length === 0} className="w-full md:w-auto px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
          {analyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyse en cours...</> : <><Search className="w-4 h-4" /> Analyser</>}
        </button>
      </div>

      {message && <div className={`rounded-lg p-4 mb-6 ${message.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'}`}>{message.text}</div>}

      {analysis && <>
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><div className="text-2xl font-bold text-gray-900">{(analysis.stats.total_variants_analyzed || 0).toLocaleString()}</div><div className="text-xs text-gray-500 mt-1">Variantes</div></div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 text-center"><div className="text-2xl font-bold text-gray-900">{(analysis.stats.markets_analyzed?.length || 0) + 1}</div><div className="text-xs text-gray-500 mt-1">Marchés</div></div>
          <div className="bg-white rounded-xl border border-red-200 p-4 text-center"><div className="text-2xl font-bold text-red-600">{analysis.stats.by_severity?.critical || 0}</div><div className="text-xs text-gray-500 mt-1">Critiques</div></div>
          <div className="bg-white rounded-xl border border-orange-200 p-4 text-center"><div className="text-2xl font-bold text-orange-600">{analysis.stats.by_severity?.warning || 0}</div><div className="text-xs text-gray-500 mt-1">Alertes</div></div>
          <div className="bg-white rounded-xl border border-yellow-200 p-4 text-center"><div className="text-2xl font-bold text-yellow-600">{analysis.stats.by_severity?.minor || 0}</div><div className="text-xs text-gray-500 mt-1">Mineurs</div></div>
          {(analysis.stats.dismissed_count || 0) > 0 && <div className="bg-white rounded-xl border border-gray-300 p-4 text-center"><div className="text-2xl font-bold text-gray-400">{analysis.stats.dismissed_count}</div><div className="text-xs text-gray-500 mt-1">Ignorées</div></div>}
        </div>

        {/* AI Summary */}
        {analysis.ai_summary && (
          <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowAiSummary(!showAiSummary)}>
              <div className="flex items-center gap-2"><Sparkles className="w-5 h-5 text-indigo-600" /><h3 className="font-semibold text-indigo-900">Analyse IA</h3></div>
              {showAiSummary ? <ChevronUp className="w-4 h-4 text-indigo-400" /> : <ChevronDown className="w-4 h-4 text-indigo-400" />}
            </div>
            {showAiSummary && <div className="mt-3 text-sm text-indigo-900 whitespace-pre-line leading-relaxed">{analysis.ai_summary}</div>}
          </div>
        )}

        {/* Type badges */}
        {analysis.stats.by_type && (
          <div className="flex gap-3 mb-4">
            {analysis.stats.by_type.intra_product > 0 && <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-700"><Layers className="w-4 h-4" /> {analysis.stats.by_type.intra_product} intra-produit</div>}
            {analysis.stats.by_type.cross_market > 0 && <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700"><Globe className="w-4 h-4" /> {analysis.stats.by_type.cross_market} cross-marchés</div>}
          </div>
        )}

        {/* Filtres */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4">
          <div className="flex flex-wrap gap-3 items-center">
            <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1) }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="all">Tous types</option><option value="intra_product">Intra-produit</option><option value="cross_market">Cross-marchés</option>
            </select>
            <select value={severityFilter} onChange={e => { setSeverityFilter(e.target.value); setPage(1) }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="all">Toutes sévérités</option><option value="critical">Critiques</option><option value="warning">Alertes</option><option value="minor">Mineurs</option>
            </select>
            <select value={marketFilter} onChange={e => { setMarketFilter(e.target.value); setPage(1) }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="all">Tous marchés</option>{anomalyMarkets.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Rechercher produit..." value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setPage(1) }} className="w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
            </div>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="severity">Sévérité</option><option value="deviation">Écart %</option><option value="product">Produit A-Z</option>
            </select>
            <button onClick={exportCSV} className="flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm hover:bg-green-200"><Download className="w-4 h-4" /> CSV</button>
          </div>
          <div className="flex flex-wrap gap-3 items-center justify-between mt-3 pt-3 border-t border-gray-100">
            <div className="flex gap-2 items-center">
              <button onClick={selectAllFiltered} className="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">Tout sélectionner ({filteredAnomalies.length})</button>
              {selectedAnomalies.size > 0 && <button onClick={deselectAll} className="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">Désélectionner</button>}
              <span className="text-sm text-gray-500">{selectedAnomalies.size} sélectionné(s)</span>
            </div>
            <button onClick={applyCorrections} disabled={applying || selectedAnomalies.size === 0} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${selectedAnomalies.size > 0 ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>
              {applying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Corriger {selectedAnomalies.size > 0 ? `(${selectedAnomalies.size})` : ''}
            </button>
            <button onClick={dismissAnomalies} disabled={dismissing || selectedAnomalies.size === 0} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${selectedAnomalies.size > 0 ? 'bg-gray-600 text-white hover:bg-gray-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}>
              {dismissing ? <Loader2 className="w-4 h-4 animate-spin" /> : <EyeOff className="w-4 h-4" />} Ignorer {selectedAnomalies.size > 0 ? `(${selectedAnomalies.size})` : ''}
            </button>
          </div>
        </div>

        {/* Table */}
        {paginatedAnomalies.length > 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="w-8 py-3 px-1"></th>
                    <th className="w-10 py-3 px-2">
                      <input type="checkbox" checked={paginatedAnomalies.every(a => selectedAnomalies.has(`${a.variant_id}-${a.market}`))} onChange={e => e.target.checked ? selectAllFiltered() : deselectAll()} className="rounded border-gray-300" />
                    </th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Sévérité</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700 min-w-[280px]">Produit</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Variante (problème)</th>
                    <th className="text-right py-3 px-3 font-medium text-gray-700">Son prix</th>
                    <th className="text-center py-3 px-2 font-medium text-gray-700">vs</th>
                    <th className="text-left py-3 px-3 font-medium text-gray-700">Variante (référence)</th>
                    <th className="text-right py-3 px-3 font-medium text-gray-700">Son prix</th>
                    <th className="text-right py-3 px-3 font-medium text-gray-700">Écart</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedAnomalies.map((a, i) => {
                    const k = `${a.variant_id}-${a.market}`
                    const sel = selectedAnomalies.has(k)
                    const expanded = expandedRows.has(k)
                    return (
                      <>
                        <tr key={`row-${i}`} className={`border-b border-gray-100 hover:bg-gray-50 ${sel ? 'bg-indigo-50' : a.severity === 'critical' ? 'bg-red-50/30' : a.severity === 'warning' ? 'bg-orange-50/30' : ''}`}>
                          <td className="py-2.5 px-1">
                            {a.context_variants && a.context_variants.length > 0 && (
                              <button onClick={() => toggleExpand(k)} className="p-0.5 hover:bg-gray-200 rounded">
                                {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                              </button>
                            )}
                          </td>
                          <td className="py-2.5 px-2" onClick={e => e.stopPropagation()}>
                            <input type="checkbox" checked={sel} onChange={() => toggleSelect(k)} className="rounded border-gray-300" />
                          </td>
                          <td className="py-2.5 px-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${getSeverityStyle(a.severity)}`}>
                              {a.severity === 'critical' && <AlertTriangle className="w-3 h-3" />}
                              {a.severity === 'warning' && <AlertCircle className="w-3 h-3" />}
                              {a.severity === 'minor' && <TrendingUp className="w-3 h-3" />}
                              {a.severity}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="font-medium text-gray-900 text-xs leading-tight" title={a.product_title}>{a.product_title || 'Produit inconnu'}</div>
                          </td>
                          <td className="py-2.5 px-3 text-sm text-red-700 font-medium">{a.variant_title || '?'}</td>
                          <td className="py-2.5 px-3 text-right text-sm text-red-600 font-semibold">{a.current_price} {a.currency}</td>
                          <td className="py-2.5 px-2 text-center text-gray-400 text-xs">devrait être ≥</td>
                          <td className="py-2.5 px-3 text-sm text-green-700 font-medium">{a.reference_variant_title || '?'}</td>
                          <td className="py-2.5 px-3 text-right text-sm text-green-600 font-semibold">{a.reference_price} {a.currency}</td>
                          <td className="py-2.5 px-3 text-right">
                            <span className={`font-semibold ${a.deviation_percent > 50 ? 'text-red-600' : a.deviation_percent > 30 ? 'text-orange-600' : 'text-yellow-600'}`}>
                              -{a.deviation_percent}%
                            </span>
                          </td>
                        </tr>
                        {/* Expanded context row */}
                        {expanded && a.context_variants && (
                          <tr key={`ctx-${i}`} className="bg-gray-50 border-b border-gray-200">
                            <td colSpan={10} className="py-3 px-6">
                              <div className="text-xs font-semibold text-gray-500 mb-2">Toutes les variantes de ce groupe (triées par taille) :</div>
                              <div className="flex flex-wrap gap-2">
                                {a.context_variants.map((cv, ci) => {
                                  const isProblematic = cv.title === a.variant_title
                                  const isReference = cv.title === a.reference_variant_title
                                  return (
                                    <div key={ci} className={`px-3 py-1.5 rounded-lg text-xs border ${isProblematic ? 'bg-red-100 border-red-300 text-red-800 font-semibold' : isReference ? 'bg-green-100 border-green-300 text-green-800 font-semibold' : 'bg-white border-gray-200 text-gray-700'}`}>
                                      {cv.title} → <span className="font-mono font-bold">{cv.price} {a.currency}</span>
                                      {isProblematic && ' ⚠️'}
                                      {isReference && ' ✓'}
                                    </div>
                                  )
                                })}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                <span className="text-sm text-gray-500">{filteredAnomalies.length} résultats — Page {page}/{totalPages}</span>
                <div className="flex gap-1">
                  <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-3 py-1 text-sm border rounded hover:bg-white disabled:opacity-50">←</button>
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const p = page <= 3 ? i + 1 : page + i - 2
                    if (p < 1 || p > totalPages) return null
                    return <button key={p} onClick={() => setPage(p)} className={`px-3 py-1 text-sm border rounded ${p === page ? 'bg-indigo-600 text-white border-indigo-600' : 'hover:bg-white'}`}>{p}</button>
                  })}
                  <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages} className="px-3 py-1 text-sm border rounded hover:bg-white disabled:opacity-50">→</button>
                </div>
              </div>
            )}
          </div>
        ) : analysis.stats.total_anomalies === 0 ? (
          <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-green-800">Aucune anomalie détectée</h3>
            <p className="text-green-600 mt-2">Tous les prix sont cohérents dans la tolérance de {tolerancePercent}%.</p>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center text-gray-500">Aucun résultat pour les filtres sélectionnés.</div>
        )}
      </>}

      {!analysis && !analyzing && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-10 text-center">
          <BarChart3 className="w-14 h-14 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-600">Prêt à analyser</h3>
          <p className="text-gray-400 mt-2 max-w-md mx-auto">Configurez les paramètres et cliquez sur "Analyser" pour détecter les incohérences de prix.</p>
        </div>
      )}
    </div>
  )
}

export default CoherenceModule
