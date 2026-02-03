import { useState, useEffect } from 'react'
import {
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Search,
  Download,
  RefreshCw,
  Loader2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Filter,
  ChevronDown,
  Check,
  X
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

function CoherenceModule() {
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [message, setMessage] = useState(null)

  // Paramètres d'analyse
  const [tolerancePercent, setTolerancePercent] = useState(15)
  const [referenceMarket, setReferenceMarket] = useState('France')
  const [availableMarkets, setAvailableMarkets] = useState([])

  // Résultats
  const [analysis, setAnalysis] = useState(null)

  // Filtres
  const [severityFilter, setSeverityFilter] = useState('all')
  const [marketFilter, setMarketFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Sélection pour correction
  const [selectedAnomalies, setSelectedAnomalies] = useState(new Set())
  const [applying, setApplying] = useState(false)

  // Charger les marchés disponibles
  useEffect(() => {
    loadMarkets()
  }, [])

  const loadMarkets = async () => {
    try {
      const response = await axios.get(`${API_URL}/pricing/coherence/markets`)
      setAvailableMarkets(response.data.markets || [])
    } catch (error) {
      console.error('Error loading markets:', error)
    }
  }

  const runAnalysis = async () => {
    try {
      setAnalyzing(true)
      setMessage(null)

      const response = await axios.post(`${API_URL}/pricing/coherence/analyze`, {
        tolerance_percent: tolerancePercent,
        reference_market: referenceMarket
      })

      setAnalysis(response.data)

      if (response.data.stats.anomalies_found === 0) {
        setMessage({ type: 'success', text: 'Aucune anomalie détectée ! Les prix sont cohérents.' })
      }
    } catch (error) {
      console.error('Analysis error:', error)
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message })
    } finally {
      setAnalyzing(false)
    }
  }

  // Filtrer les anomalies
  const filteredAnomalies = analysis?.anomalies?.filter(a => {
    if (severityFilter !== 'all' && a.severity !== severityFilter) return false
    if (marketFilter !== 'all' && a.comparison_market !== marketFilter) return false
    if (searchQuery && !a.variant_id.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  }) || []

  // Sélection des anomalies
  const toggleSelectAnomaly = (anomalyKey) => {
    const newSelected = new Set(selectedAnomalies)
    if (newSelected.has(anomalyKey)) {
      newSelected.delete(anomalyKey)
    } else {
      newSelected.add(anomalyKey)
    }
    setSelectedAnomalies(newSelected)
  }

  const selectAllFiltered = () => {
    const newSelected = new Set(selectedAnomalies)
    filteredAnomalies.forEach(a => {
      newSelected.add(`${a.variant_id}-${a.comparison_market}`)
    })
    setSelectedAnomalies(newSelected)
  }

  const deselectAll = () => {
    setSelectedAnomalies(new Set())
  }

  // Appliquer les corrections
  const applyCorrections = async () => {
    if (selectedAnomalies.size === 0) {
      setMessage({ type: 'error', text: 'Sélectionnez au moins une anomalie à corriger' })
      return
    }

    const corrections = analysis.anomalies
      .filter(a => selectedAnomalies.has(`${a.variant_id}-${a.comparison_market}`))
      .map(a => ({
        variant_id: a.variant_id,
        market: a.comparison_market,
        suggested_price: a.suggested_price,
        currency: a.market_currency
      }))

    if (!window.confirm(`Voulez-vous corriger ${corrections.length} prix ?`)) return

    try {
      setApplying(true)
      setMessage(null)

      const response = await axios.post(`${API_URL}/pricing/coherence/apply`, {
        corrections,
        dry_run: false
      })

      if (response.data.applied) {
        setMessage({
          type: 'success',
          text: `✅ ${response.data.results.updated_count} prix corrigés avec succès !`
        })
        setSelectedAnomalies(new Set())
        // Relancer l'analyse pour voir les changements
        setTimeout(() => runAnalysis(), 1000)
      }
    } catch (error) {
      console.error('Apply error:', error)
      setMessage({ type: 'error', text: error.response?.data?.detail || error.message })
    } finally {
      setApplying(false)
    }
  }

  // Exporter en CSV
  const exportCSV = () => {
    if (!analysis?.anomalies) return

    const headers = ['Variant ID', 'Marché Référence', 'Prix Référence', 'Marché Comparé', 'Prix Actuel', 'Prix Attendu', 'Écart %', 'Sévérité']
    const rows = analysis.anomalies.map(a => [
      a.variant_id,
      a.reference_market,
      `${a.reference_price} ${a.reference_currency}`,
      a.comparison_market,
      `${a.actual_price} ${a.market_currency}`,
      `${a.expected_price} ${a.market_currency}`,
      `${a.deviation_percent}%`,
      a.severity
    ])

    const csv = [headers, ...rows].map(row => row.join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `coherence_analysis_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'critical': return 'bg-red-100 text-red-700 border-red-200'
      case 'warning': return 'bg-orange-100 text-orange-700 border-orange-200'
      case 'minor': return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const getSeverityIcon = (severity) => {
    switch(severity) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'warning': return <AlertCircle className="w-4 h-4 text-orange-500" />
      case 'minor': return <TrendingUp className="w-4 h-4 text-yellow-500" />
      default: return null
    }
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-title flex items-center gap-3">
          <BarChart3 className="w-7 h-7" />
          Analyse de Cohérence
        </h1>
        <p className="text-luxarmonie-gray-500 mt-1">
          Détectez les incohérences de prix entre vos marchés internationaux
        </p>
      </div>

      {/* Messages */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          message.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
          'bg-yellow-50 text-yellow-700 border border-yellow-200'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Paramètres d'analyse */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Filter className="w-5 h-5" />
          Paramètres d'analyse
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {/* Marché de référence */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Marché de référence
            </label>
            <select
              value={referenceMarket}
              onChange={(e) => setReferenceMarket(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {availableMarkets.map(m => (
                <option key={m.name || m} value={m.name || m}>
                  {m.name || m} {m.currency ? `(${m.currency})` : ''}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Les prix des autres marchés seront comparés à ce marché
            </p>
          </div>

          {/* Tolérance */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tolérance d'écart (%)
            </label>
            <input
              type="number"
              value={tolerancePercent}
              onChange={(e) => setTolerancePercent(parseFloat(e.target.value) || 15)}
              min="1"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Écart acceptable entre prix attendu et prix réel
            </p>
          </div>

          {/* Bouton analyse */}
          <div className="flex items-end">
            <button
              onClick={runAnalysis}
              disabled={analyzing}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyse en cours...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Analyser
                </>
              )}
            </button>
          </div>
        </div>

        {/* Info */}
        <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-700">
          <strong>Comment ça marche :</strong> L'analyse compare les prix de chaque variante entre le marché de référence
          et les autres marchés, en tenant compte des taux de change configurés. Les écarts supérieurs à la tolérance sont signalés.
        </div>
      </div>

      {/* Résultats */}
      {analysis && (
        <>
          {/* Statistiques */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 text-center">
              <div className="text-2xl font-bold text-gray-900">{analysis.stats.total_variants_analyzed}</div>
              <div className="text-xs text-gray-500">Variantes analysées</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 text-center">
              <div className="text-2xl font-bold text-gray-900">{analysis.stats.markets_analyzed?.length || 0}</div>
              <div className="text-xs text-gray-500">Marchés comparés</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-red-200 text-center">
              <div className="text-2xl font-bold text-red-600">{analysis.stats.by_severity?.critical || 0}</div>
              <div className="text-xs text-red-500">Critiques</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-orange-200 text-center">
              <div className="text-2xl font-bold text-orange-600">{analysis.stats.by_severity?.warning || 0}</div>
              <div className="text-xs text-orange-500">Alertes</div>
            </div>
            <div className="bg-white rounded-xl p-4 shadow-sm border border-yellow-200 text-center">
              <div className="text-2xl font-bold text-yellow-600">{analysis.stats.by_severity?.minor || 0}</div>
              <div className="text-xs text-yellow-500">Mineurs</div>
            </div>
          </div>

          {/* Filtres, sélection et actions */}
          {analysis.anomalies?.length > 0 && (
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 mb-4">
              <div className="flex flex-wrap gap-4 items-center justify-between mb-3">
                <div className="flex gap-3 items-center">
                  {/* Filtre sévérité */}
                  <select
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="all">Toutes sévérités</option>
                    <option value="critical">Critiques</option>
                    <option value="warning">Alertes</option>
                    <option value="minor">Mineurs</option>
                  </select>

                  {/* Filtre marché */}
                  <select
                    value={marketFilter}
                    onChange={(e) => setMarketFilter(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                  >
                    <option value="all">Tous les marchés</option>
                    {analysis.stats.markets_analyzed?.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>

                  {/* Recherche */}
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Rechercher variant ID..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm w-48"
                    />
                  </div>
                </div>

                <div className="flex gap-2">
                  {/* Export */}
                  <button
                    onClick={exportCSV}
                    className="flex items-center gap-2 px-4 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm hover:bg-green-200"
                  >
                    <Download className="w-4 h-4" />
                    Exporter CSV
                  </button>
                </div>
              </div>

              {/* Barre de sélection et correction */}
              <div className="flex flex-wrap gap-3 items-center justify-between pt-3 border-t border-gray-200">
                <div className="flex gap-2 items-center">
                  <button
                    onClick={selectAllFiltered}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Tout sélectionner ({filteredAnomalies.length})
                  </button>
                  {selectedAnomalies.size > 0 && (
                    <button
                      onClick={deselectAll}
                      className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      Désélectionner tout
                    </button>
                  )}
                  <span className="text-sm text-gray-500">
                    {selectedAnomalies.size} sélectionné(s)
                  </span>
                </div>

                {/* Bouton Corriger */}
                <button
                  onClick={applyCorrections}
                  disabled={applying || selectedAnomalies.size === 0}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedAnomalies.size > 0
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {applying ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Correction en cours...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Corriger {selectedAnomalies.size > 0 ? `(${selectedAnomalies.size})` : ''}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Liste des anomalies */}
          {filteredAnomalies.length > 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="w-10 py-3 px-2">
                        <input
                          type="checkbox"
                          checked={filteredAnomalies.length > 0 && filteredAnomalies.every(a => selectedAnomalies.has(`${a.variant_id}-${a.comparison_market}`))}
                          onChange={(e) => e.target.checked ? selectAllFiltered() : deselectAll()}
                          className="rounded border-gray-300"
                        />
                      </th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Sévérité</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Variant ID</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Marché</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-700">Prix actuel</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-700">Prix suggéré</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-700">Écart</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAnomalies.slice(0, 100).map((anomaly, idx) => {
                      const anomalyKey = `${anomaly.variant_id}-${anomaly.comparison_market}`
                      const isSelected = selectedAnomalies.has(anomalyKey)

                      return (
                        <tr key={idx} className={`border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                          isSelected ? 'bg-blue-50' :
                          anomaly.severity === 'critical' ? 'bg-red-50/50' :
                          anomaly.severity === 'warning' ? 'bg-orange-50/50' : ''
                        }`}
                        onClick={() => toggleSelectAnomaly(anomalyKey)}
                        >
                          <td className="py-2 px-2" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelectAnomaly(anomalyKey)}
                              className="rounded border-gray-300"
                            />
                          </td>
                          <td className="py-2 px-4">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(anomaly.severity)}`}>
                              {getSeverityIcon(anomaly.severity)}
                              {anomaly.severity}
                            </span>
                          </td>
                          <td className="py-2 px-4 font-mono text-xs truncate max-w-[150px]" title={anomaly.variant_id}>
                            {anomaly.variant_id.split('/').pop()}
                          </td>
                          <td className="py-2 px-4">{anomaly.comparison_market}</td>
                          <td className="py-2 px-4 text-right font-medium text-gray-500 line-through">
                            {anomaly.actual_price} {anomaly.market_currency}
                          </td>
                          <td className="py-2 px-4 text-right font-medium text-green-600">
                            {anomaly.suggested_price} {anomaly.market_currency}
                          </td>
                          <td className="py-2 px-4 text-right">
                            <span className={`font-medium ${
                              anomaly.deviation_percent > 30 ? 'text-red-600' :
                              anomaly.deviation_percent > 20 ? 'text-orange-600' :
                              'text-yellow-600'
                            }`}>
                              {anomaly.actual_price > anomaly.expected_price ? '+' : '-'}{anomaly.deviation_percent}%
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              {filteredAnomalies.length > 100 && (
                <div className="p-4 text-center text-sm text-gray-500 border-t border-gray-200">
                  Affichage limité à 100 lignes. Exportez en CSV pour voir toutes les anomalies.
                </div>
              )}
            </div>
          ) : analysis.anomalies?.length === 0 ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-green-800">Aucune anomalie détectée</h3>
              <p className="text-green-600 mt-2">
                Tous les prix sont cohérents avec le marché de référence ({referenceMarket})
                dans la tolérance de {tolerancePercent}%.
              </p>
            </div>
          ) : null}
        </>
      )}

      {/* État initial */}
      {!analysis && !analyzing && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-8 text-center">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-700">Prêt à analyser</h3>
          <p className="text-gray-500 mt-2">
            Configurez les paramètres ci-dessus et cliquez sur "Analyser" pour détecter
            les incohérences de prix entre vos marchés.
          </p>
        </div>
      )}
    </div>
  )
}

export default CoherenceModule
