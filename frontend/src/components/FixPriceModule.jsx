import { useState, useEffect } from 'react'
import { 
  Wrench, 
  Search, 
  Copy, 
  DollarSign,
  Check, 
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  X,
  ArrowRight,
  Target,
  Package
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

function FixPriceModule() {
  // Mode: 'fix' pour prix fixe, 'copy' pour copier variante
  const [mode, setMode] = useState('fix')
  
  // États communs
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [products, setProducts] = useState([])
  const [productSearch, setProductSearch] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  
  // États pour Mode "Prix Fixe"
  const [selectedVariants, setSelectedVariants] = useState([])
  const [basePriceEur, setBasePriceEur] = useState('')
  const [compareAtPriceEur, setCompareAtPriceEur] = useState('')
  const [fixPreview, setFixPreview] = useState(null)
  const [excludedMarkets, setExcludedMarkets] = useState(new Set())
  
  // États pour Mode "Copier Variante"
  const [sourceVariant, setSourceVariant] = useState(null)
  const [targetVariants, setTargetVariants] = useState([])
  const [copyPreview, setCopyPreview] = useState(null)
  
  // Expanded products pour afficher les variantes
  const [expandedProducts, setExpandedProducts] = useState({})

  // ========================================
  // RECHERCHE DE PRODUITS
  // ========================================
  
  const searchProducts = async (query) => {
    if (query.length < 2) {
      setProducts([])
      return
    }
    
    try {
      setSearchLoading(true)
      const response = await axios.get(`${API_URL}/products?search=${encodeURIComponent(query)}&limit=20`)
      setProducts(response.data.products || [])
    } catch (error) {
      console.error('Error searching products:', error)
      setProducts([])
    } finally {
      setSearchLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      if (productSearch) {
        searchProducts(productSearch)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [productSearch])

  // ========================================
  // MODE PRIX FIXE - HANDLERS
  // ========================================
  
  const handleSelectVariantForFix = (product, variant) => {
    const variantData = {
      variantId: variant.id,
      variantTitle: variant.title,
      productTitle: product.title,
      productId: product.id,
      currentPrice: variant.price,
      sku: variant.sku
    }

    // Vérifier si déjà sélectionné
    if (!selectedVariants.find(v => v.variantId === variant.id)) {
      setSelectedVariants([...selectedVariants, variantData])
    }
  }

  const handleSelectAllVariantsForFix = (product) => {
    const newVariants = product.variants
      .filter(v => !selectedVariants.find(sv => sv.variantId === v.id))
      .map(variant => ({
        variantId: variant.id,
        variantTitle: variant.title,
        productTitle: product.title,
        productId: product.id,
        currentPrice: variant.price,
        sku: variant.sku
      }))

    setSelectedVariants([...selectedVariants, ...newVariants])
  }

  const handleDeselectAllVariantsForProduct = (productId) => {
    setSelectedVariants(selectedVariants.filter(v => v.productId !== productId))
  }
  
  const handleRemoveVariantFromFix = (variantId) => {
    setSelectedVariants(selectedVariants.filter(v => v.variantId !== variantId))
  }
  
  const handleFixPreview = async () => {
    if (selectedVariants.length === 0 || !basePriceEur) {
      setMessage({ type: 'error', text: 'Sélectionnez des variantes et entrez un prix' })
      return
    }
    
    try {
      setLoading(true)
      setMessage(null)
      
      const response = await axios.post(`${API_URL}/fix-price/preview`, {
        variant_ids: selectedVariants.map(v => v.variantId),
        base_price_eur: parseFloat(basePriceEur),
        compare_at_price_eur: compareAtPriceEur ? parseFloat(compareAtPriceEur) : null,
        countries: ['all']
      })
      
      setFixPreview(response.data)
      setExcludedMarkets(new Set())
    } catch (error) {
      console.error('Fix preview error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  const handleFixApply = async () => {
    if (!fixPreview) return
    
    // Filtrer les marchés exclus
    const includedPreview = (fixPreview.preview || []).filter(row => !excludedMarkets.has(row.country))
    const includedCountries = [...new Set(includedPreview.map(row => row.country))]
    
    if (includedCountries.length === 0) {
      setMessage({ type: 'error', text: 'Aucun marché sélectionné.' })
      return
    }
    
    if (!window.confirm(`Vous allez modifier ${includedPreview.length} prix sur ${includedCountries.length} marchés. Continuer ?`)) {
      return
    }
    
    try {
      setLoading(true)
      
      const response = await axios.post(`${API_URL}/fix-price/apply`, {
        variant_ids: selectedVariants.map(v => v.variantId),
        base_price_eur: parseFloat(basePriceEur),
        compare_at_price_eur: compareAtPriceEur ? parseFloat(compareAtPriceEur) : null,
        countries: includedCountries
      })
      
      if (response.data.applied) {
        setMessage({ 
          type: 'success', 
          text: `✅ ${response.data.results.updated_count} prix mis à jour avec succès !` 
        })
        setFixPreview(null)
        setSelectedVariants([])
        setBasePriceEur('')
        setCompareAtPriceEur('')
      }
    } catch (error) {
      console.error('Fix apply error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  // ========================================
  // MODE COPIER VARIANTE - HANDLERS
  // ========================================
  
  const handleSelectSourceVariant = (product, variant) => {
    setSourceVariant({
      variantId: variant.id,
      variantTitle: variant.title,
      productTitle: product.title,
      productId: product.id,
      currentPrice: variant.price
    })
    setProductSearch('')
    setProducts([])
  }
  
  const handleSelectTargetVariant = (product, variant) => {
    if (sourceVariant && variant.id === sourceVariant.variantId) {
      setMessage({ type: 'error', text: 'Impossible de copier vers la même variante' })
      return
    }
    
    const variantData = {
      variantId: variant.id,
      variantTitle: variant.title,
      productTitle: product.title,
      productId: product.id,
      currentPrice: variant.price
    }
    
    if (!targetVariants.find(v => v.variantId === variant.id)) {
      setTargetVariants([...targetVariants, variantData])
    }
    
    setProductSearch('')
    setProducts([])
  }
  
  const handleRemoveTargetVariant = (variantId) => {
    setTargetVariants(targetVariants.filter(v => v.variantId !== variantId))
  }
  
  const handleCopyPreview = async () => {
    if (!sourceVariant || targetVariants.length === 0) {
      setMessage({ type: 'error', text: 'Sélectionnez une variante source et au moins une cible' })
      return
    }
    
    try {
      setLoading(true)
      setMessage(null)
      
      const response = await axios.post(`${API_URL}/fix-price/copy/preview`, {
        source_variant_id: sourceVariant.variantId,
        target_variant_ids: targetVariants.map(v => v.variantId),
        countries: ['all']
      })
      
      setCopyPreview(response.data)
    } catch (error) {
      console.error('Copy preview error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  const handleCopyApply = async () => {
    if (!copyPreview) return
    
    if (!window.confirm(`Vous allez copier les prix vers ${copyPreview.summary.target_variants_count} variantes. Continuer ?`)) {
      return
    }
    
    try {
      setLoading(true)
      
      const response = await axios.post(`${API_URL}/fix-price/copy/apply`, {
        source_variant_id: sourceVariant.variantId,
        target_variant_ids: targetVariants.map(v => v.variantId),
        countries: ['all']
      })
      
      if (response.data.applied) {
        setMessage({ 
          type: 'success', 
          text: `✅ ${response.data.results.updated_count} prix copiés avec succès !` 
        })
        setCopyPreview(null)
        setSourceVariant(null)
        setTargetVariants([])
      }
    } catch (error) {
      console.error('Copy apply error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  // ========================================
  // TOGGLE PRODUCT EXPAND
  // ========================================
  
  const toggleProductExpand = (productId) => {
    setExpandedProducts(prev => ({
      ...prev,
      [productId]: !prev[productId]
    }))
  }

  // ========================================
  // RENDER
  // ========================================

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-title flex items-center gap-3">
          <Wrench className="w-7 h-7" />
          Correction de Prix
        </h1>
        <p className="text-luxarmonie-gray-500 mt-1">
          Corrigez les prix de variantes spécifiques sur tous les marchés
        </p>
      </div>

      {/* Mode Selector */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => { setMode('fix'); setMessage(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            mode === 'fix'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          Prix Fixe
        </button>
        <button
          onClick={() => { setMode('copy'); setMessage(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
            mode === 'copy'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Copy className="w-4 h-4" />
          Copier Variante
        </button>
      </div>

      {/* Messages */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' :
          message.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
          'bg-yellow-50 text-yellow-700 border border-yellow-200'
        }`}>
          {message.type === 'success' ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* ========================================
          MODE PRIX FIXE
          ======================================== */}
      {mode === 'fix' && (
        <div className="space-y-6">
          {/* Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <h3 className="font-medium text-blue-800 mb-2">💡 Mode Prix Fixe</h3>
            <p className="text-sm text-blue-600">
              Définissez un prix EUR de référence et le Hub calculera automatiquement les prix 
              pour tous les marchés avec les bons taux de change et terminaisons psychologiques.
            </p>
          </div>

          {/* Recherche de variantes */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Package className="w-5 h-5" />
              1. Sélectionner les variantes à corriger
            </h3>
            
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher un produit..."
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {searchLoading && (
                <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
              )}
            </div>

            {/* Résultats de recherche */}
            {products.length > 0 && (
              <div className="mt-2 border border-gray-200 rounded-lg max-h-80 overflow-y-auto">
                {products.map(product => (
                  <div key={product.id} className="border-b border-gray-100 last:border-b-0">
                    <div className="flex items-center justify-between px-4 py-2 hover:bg-gray-50">
                      <button
                        onClick={() => toggleProductExpand(product.id)}
                        className="flex items-center gap-2 flex-1 text-left"
                      >
                        {expandedProducts[product.id] ? (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-400" />
                        )}
                        <span className="font-medium text-sm">{product.title}</span>
                        <span className="text-xs text-gray-400">({product.variants?.length} variantes)</span>
                      </button>
                      <button
                        onClick={() => handleSelectAllVariantsForFix(product)}
                        className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        + Tout sélectionner
                      </button>
                    </div>

                    {expandedProducts[product.id] && (
                      <div className="bg-gray-50 px-4 py-2">
                        {product.variants?.map(variant => {
                          const isSelected = selectedVariants.find(v => v.variantId === variant.id)
                          return (
                            <button
                              key={variant.id}
                              onClick={() => handleSelectVariantForFix(product, variant)}
                              disabled={isSelected}
                              className={`w-full text-left px-3 py-1.5 text-sm rounded flex justify-between items-center ${
                                isSelected
                                  ? 'bg-blue-100 text-blue-700 cursor-default'
                                  : 'hover:bg-blue-100'
                              }`}
                            >
                              <span className="flex items-center gap-2">
                                {isSelected && <Check className="w-3 h-3" />}
                                {variant.title}
                                {variant.sku && <span className="text-xs text-gray-400">({variant.sku})</span>}
                              </span>
                              <span className="text-gray-500">{variant.price} €</span>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Variantes sélectionnées - Groupées par produit */}
            {selectedVariants.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Variantes sélectionnées ({selectedVariants.length})
                </h4>
                <div className="space-y-2">
                  {/* Grouper par produit */}
                  {Object.entries(
                    selectedVariants.reduce((acc, v) => {
                      if (!acc[v.productId]) {
                        acc[v.productId] = { title: v.productTitle, variants: [] }
                      }
                      acc[v.productId].variants.push(v)
                      return acc
                    }, {})
                  ).map(([productId, { title, variants }]) => (
                    <div key={productId} className="bg-blue-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-sm text-blue-900">{title}</span>
                        <button
                          onClick={() => handleDeselectAllVariantsForProduct(productId)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          Tout retirer
                        </button>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {variants.map(v => (
                          <div key={v.variantId} className="flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs">
                            <span>{v.variantTitle}</span>
                            <button onClick={() => handleRemoveVariantFromFix(v.variantId)} className="hover:text-red-600">
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Prix de référence */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              2. Définir le prix de référence (EUR)
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prix de vente (EUR) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={basePriceEur}
                  onChange={(e) => setBasePriceEur(e.target.value)}
                  placeholder="Ex: 134.99"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Prix barré (EUR) <span className="text-gray-400">optionnel</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={compareAtPriceEur}
                  onChange={(e) => setCompareAtPriceEur(e.target.value)}
                  placeholder="Ex: 189.99"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4">
            <button
              onClick={handleFixPreview}
              disabled={loading || selectedVariants.length === 0 || !basePriceEur}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Prévisualiser
            </button>
            
            {fixPreview && (
              <button
                onClick={handleFixApply}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Appliquer ({(fixPreview.preview || []).filter(r => !excludedMarkets.has(r.country)).length} modifications)
              </button>
            )}
          </div>

          {/* Preview */}
          {fixPreview && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-blue-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Prévisualisation</h3>
                <button onClick={() => setFixPreview(null)} className="text-gray-400 hover:text-gray-600">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{fixPreview.summary.variants_count}</div>
                  <div className="text-xs text-blue-500">Variantes</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{fixPreview.summary.countries_count - excludedMarkets.size}</div>
                  <div className="text-xs text-blue-500">Marchés</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{(fixPreview.preview || []).filter(r => !excludedMarkets.has(r.country)).length}</div>
                  <div className="text-xs text-blue-500">Modifications</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-blue-600">{fixPreview.summary.base_price_eur}€</div>
                  <div className="text-xs text-blue-500">Prix EUR</div>
                </div>
              </div>

              {/* Sélection marchés */}
              <div className="flex gap-2 items-center mb-3 pb-3 border-b border-gray-100">
                <button onClick={() => setExcludedMarkets(new Set())} className="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">Tout inclure</button>
                <button onClick={() => {
                  const allMarkets = new Set((fixPreview.preview || []).map(r => r.country))
                  setExcludedMarkets(allMarkets)
                }} className="text-xs px-3 py-1 bg-gray-100 rounded hover:bg-gray-200">Tout exclure</button>
                {excludedMarkets.size > 0 && <span className="text-xs text-orange-600">{excludedMarkets.size} marché(s) exclu(s)</span>}
              </div>

              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="w-8 py-2 px-2">
                        <input type="checkbox" checked={excludedMarkets.size === 0} onChange={e => e.target.checked ? setExcludedMarkets(new Set()) : setExcludedMarkets(new Set((fixPreview.preview || []).map(r => r.country)))} className="rounded border-gray-300" />
                      </th>
                      <th className="text-left py-2 px-3">Variante</th>
                      <th className="text-left py-2 px-3">Marché</th>
                      <th className="text-right py-2 px-3">Ancien prix</th>
                      <th className="text-right py-2 px-3">Nouveau prix</th>
                      <th className="text-right py-2 px-3">Diff</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fixPreview.preview?.map((row, idx) => {
                      const excluded = excludedMarkets.has(row.country)
                      return (
                        <tr key={idx} className={`border-b border-gray-100 ${excluded ? 'opacity-30' : ''}`}>
                          <td className="py-2 px-2">
                            <input type="checkbox" checked={!excluded} onChange={() => {
                              const s = new Set(excludedMarkets)
                              excluded ? s.delete(row.country) : s.add(row.country)
                              setExcludedMarkets(s)
                            }} className="rounded border-gray-300" />
                          </td>
                          <td className="py-2 px-3 truncate max-w-[150px]">{row.variant_title}</td>
                          <td className="py-2 px-3">{row.country}</td>
                          <td className="py-2 px-3 text-right text-gray-500">
                            {row.current_price || '-'} {row.currency}
                          </td>
                          <td className="py-2 px-3 text-right font-medium text-green-600">
                            {row.new_price} {row.currency}
                          </td>
                          <td className="py-2 px-3 text-right">
                            {row.price_diff_percent !== null && (
                              <span className={`px-2 py-0.5 rounded text-xs ${
                                row.price_diff_percent > 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                              }`}>
                                {row.price_diff_percent > 0 ? '+' : ''}{row.price_diff_percent}%
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================
          MODE COPIER VARIANTE
          ======================================== */}
      {mode === 'copy' && (
        <div className="space-y-6">
          {/* Instructions */}
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
            <h3 className="font-medium text-purple-800 mb-2">💡 Mode Copier Variante</h3>
            <p className="text-sm text-purple-600">
              Sélectionnez une variante "modèle" avec les bons prix, puis copiez-les vers d'autres variantes 
              sur tous les marchés.
            </p>
          </div>

          {/* Variante Source */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-600" />
              1. Sélectionner la variante source (modèle)
            </h3>
            
            {!sourceVariant ? (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Rechercher le produit avec les bons prix..."
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>

                {products.length > 0 && (
                  <div className="mt-2 border border-gray-200 rounded-lg max-h-64 overflow-y-auto">
                    {products.map(product => (
                      <div key={product.id} className="border-b border-gray-100 last:border-b-0">
                        <button
                          onClick={() => toggleProductExpand(product.id)}
                          className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50"
                        >
                          <span className="font-medium text-sm">{product.title}</span>
                          {expandedProducts[product.id] ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                        
                        {expandedProducts[product.id] && (
                          <div className="bg-gray-50 px-4 py-2">
                            {product.variants?.map(variant => (
                              <button
                                key={variant.id}
                                onClick={() => handleSelectSourceVariant(product, variant)}
                                className="w-full text-left px-3 py-1.5 text-sm hover:bg-purple-100 rounded flex justify-between items-center"
                              >
                                <span>{variant.title}</span>
                                <span className="text-gray-500">{variant.price} €</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-between bg-purple-100 text-purple-800 px-4 py-3 rounded-lg">
                <div>
                  <div className="font-medium">{sourceVariant.productTitle}</div>
                  <div className="text-sm">{sourceVariant.variantTitle} - {sourceVariant.currentPrice} €</div>
                </div>
                <button 
                  onClick={() => { setSourceVariant(null); setCopyPreview(null); }}
                  className="text-purple-600 hover:text-purple-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>

          {/* Variantes Cibles */}
          {sourceVariant && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <ArrowRight className="w-5 h-5 text-green-600" />
                2. Sélectionner les variantes à modifier
              </h3>
              
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Rechercher les variantes cibles..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>

              {products.length > 0 && (
                <div className="mt-2 border border-gray-200 rounded-lg max-h-64 overflow-y-auto">
                  {products.map(product => (
                    <div key={product.id} className="border-b border-gray-100 last:border-b-0">
                      <button
                        onClick={() => toggleProductExpand(product.id)}
                        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-50"
                      >
                        <span className="font-medium text-sm">{product.title}</span>
                        {expandedProducts[product.id] ? (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      
                      {expandedProducts[product.id] && (
                        <div className="bg-gray-50 px-4 py-2">
                          {product.variants?.map(variant => (
                            <button
                              key={variant.id}
                              onClick={() => handleSelectTargetVariant(product, variant)}
                              disabled={variant.id === sourceVariant.variantId}
                              className={`w-full text-left px-3 py-1.5 text-sm rounded flex justify-between items-center ${
                                variant.id === sourceVariant.variantId 
                                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed' 
                                  : 'hover:bg-green-100'
                              }`}
                            >
                              <span>{variant.title}</span>
                              <span className="text-gray-500">{variant.price} €</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Variantes cibles sélectionnées */}
              {targetVariants.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Variantes cibles ({targetVariants.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {targetVariants.map(v => (
                      <div key={v.variantId} className="flex items-center gap-2 bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                        <span className="truncate max-w-[200px]">{v.productTitle} - {v.variantTitle}</span>
                        <button onClick={() => handleRemoveTargetVariant(v.variantId)}>
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          {sourceVariant && (
            <div className="flex gap-4">
              <button
                onClick={handleCopyPreview}
                disabled={loading || targetVariants.length === 0}
                className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Prévisualiser
              </button>
              
              {copyPreview && (
                <button
                  onClick={handleCopyApply}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Copier ({copyPreview.summary.total_updates} modifications)
                </button>
              )}
            </div>
          )}

          {/* Preview */}
          {copyPreview && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-purple-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Prévisualisation de la copie</h3>
                <button onClick={() => setCopyPreview(null)} className="text-gray-400 hover:text-gray-600">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-purple-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-purple-600">{copyPreview.summary.target_variants_count}</div>
                  <div className="text-xs text-purple-500">Variantes cibles</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-purple-600">{copyPreview.summary.countries_count}</div>
                  <div className="text-xs text-purple-500">Marchés</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-purple-600">{copyPreview.summary.total_updates}</div>
                  <div className="text-xs text-purple-500">Modifications</div>
                </div>
              </div>

              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left py-2 px-3">Variante cible</th>
                      <th className="text-left py-2 px-3">Marché</th>
                      <th className="text-right py-2 px-3">Ancien prix</th>
                      <th className="text-right py-2 px-3">Nouveau prix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {copyPreview.preview?.slice(0, 50).map((row, idx) => (
                      <tr key={idx} className="border-b border-gray-100">
                        <td className="py-2 px-3 truncate max-w-[150px]">{row.target_title}</td>
                        <td className="py-2 px-3">{row.country}</td>
                        <td className="py-2 px-3 text-right text-gray-500">
                          {row.current_price || '-'} {row.currency}
                        </td>
                        <td className="py-2 px-3 text-right font-medium text-green-600">
                          {row.new_price} {row.currency}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FixPriceModule
