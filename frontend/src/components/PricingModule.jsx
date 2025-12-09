import { useState, useEffect, useCallback } from 'react'
import { 
  Globe, 
  Package, 
  Settings2, 
  Eye, 
  Check, 
  AlertCircle,
  Search,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  Database,
  ServerCog,
  Sparkles,
  Percent
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'
const API_BASE = import.meta.env.VITE_API_URL || ''

// ========================================
// COMPOSANT STATUS DU CACHE
// ========================================
function CacheStatus({ onCacheLoaded }) {
  const [status, setStatus] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [wasLoading, setWasLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/cache/status`)
      const newStatus = response.data
      
      // Si le cache vient de finir de charger, notifier le parent
      if (wasLoading && newStatus.loaded && !newStatus.loading) {
        console.log("Cache finished loading, reloading countries...")
        if (onCacheLoaded) {
          onCacheLoaded()
        }
      }
      
      setWasLoading(newStatus.loading)
      setStatus(newStatus)
    } catch (error) {
      console.error('Error fetching cache status:', error)
    }
  }, [onCacheLoaded, wasLoading])

  useEffect(() => {
    fetchStatus()
    // Polling toutes les 5 secondes si le cache est en cours de chargement
    const interval = setInterval(() => {
      fetchStatus()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await axios.post(`${API_URL}/cache/refresh`)
      // Le polling va mettre à jour le statut
    } catch (error) {
      console.error('Error refreshing cache:', error)
    }
    setTimeout(() => setRefreshing(false), 2000)
  }

  if (!status) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Connexion au serveur...</span>
        </div>
      </div>
    )
  }

  const isLoading = status.loading
  const isLoaded = status.loaded

  return (
    <div className={`border rounded-lg p-4 mb-6 ${
      isLoaded ? 'bg-green-50 border-green-200' : 
      isLoading ? 'bg-yellow-50 border-yellow-200' : 
      'bg-gray-50 border-gray-200'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ServerCog className={`w-5 h-5 ${
            isLoaded ? 'text-green-600' : 
            isLoading ? 'text-yellow-600' : 
            'text-gray-400'
          }`} />
          <div>
            <div className="font-medium text-gray-900">
              {isLoaded ? '✅ Cache des prix chargé' : 
               isLoading ? '⏳ Chargement du cache en cours...' : 
               '⚠️ Cache non chargé'}
            </div>
            <div className="text-sm text-gray-500">
              {isLoaded && (
                <>
                  {status.markets_count} marchés • {status.total_prices?.toLocaleString()} prix
                  {status.last_refresh && (
                    <span className="ml-2">
                      • MàJ: {new Date(status.last_refresh).toLocaleTimeString()}
                    </span>
                  )}
                </>
              )}
              {isLoading && status.progress && (
                <>
                  {status.progress.current_market} ({status.progress.markets_done}/{status.progress.total_markets})
                  • {status.progress.total_prices?.toLocaleString()} prix chargés
                </>
              )}
              {!isLoaded && !isLoading && (
                <span>Cliquez sur Rafraîchir pour charger les prix actuels</span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading || refreshing}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            isLoading || refreshing 
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
              : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
        >
          <RefreshCw className={`w-4 h-4 ${(isLoading || refreshing) ? 'animate-spin' : ''}`} />
          {isLoading ? 'Chargement...' : 'Rafraîchir'}
        </button>
      </div>
      
      {isLoading && status.progress && (
        <div className="mt-3">
          <div className="w-full bg-yellow-100 rounded-full h-2">
            <div 
              className="bg-yellow-500 h-2 rounded-full transition-all duration-500"
              style={{ 
                width: `${status.progress.total_markets > 0 
                  ? (status.progress.markets_done / status.progress.total_markets) * 100 
                  : 0}%` 
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function PricingModule() {
  // États
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [countries, setCountries] = useState([])
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectAllCountries, setSelectAllCountries] = useState(false)
  const [products, setProducts] = useState([])
  const [selectedProducts, setSelectedProducts] = useState([])
  const [selectedVariants, setSelectedVariants] = useState({})
  const [expandedProducts, setExpandedProducts] = useState({})
  const [productMode, setProductMode] = useState('all') // 'all', 'search', 'selected'
  const [productSearch, setProductSearch] = useState('')
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [showProductDropdown, setShowProductDropdown] = useState(false)
  
  // Paramètres de pricing
  const [settings, setSettings] = useState({
    baseAdjustment: 10,  // +10%
    applyVat: false,
    discount: 40  // 40% de réduction affichée
  })
  
  // Preview
  const [preview, setPreview] = useState(null)
  const [showPreview, setShowPreview] = useState(false)
  
  // Progression de l'apply
  const [applyProgress, setApplyProgress] = useState(null)
  
  // Promos Aléatoires
  const [showPromoModule, setShowPromoModule] = useState(false)
  const [promoSettings, setPromoSettings] = useState({
    catalogPercentage: 50,
    minDiscount: 10,
    maxDiscount: 40
  })
  const [promoPreview, setPromoPreview] = useState(null)
  const [promoSeed, setPromoSeed] = useState(null)
  
  // Messages
  const [message, setMessage] = useState(null)

  // Charger les pays au montage
  useEffect(() => {
    loadCountries()
  }, [])

  const loadCountries = async () => {
    try {
      const response = await axios.get(`${API_URL}/pricing/config`)
      setCountries(response.data.countries || [])
    } catch (error) {
      console.error('Error loading countries:', error)
      setCountries([
        { name: 'France', currency: 'EUR', vat: 0.19 },
        { name: 'Allemagne', currency: 'EUR', vat: 0.19 },
        { name: 'USA', currency: 'USD', vat: 0 },
        { name: 'UK', currency: 'GBP', vat: 0 },
      ])
    }
  }

  const searchProducts = async (query) => {
    if (query.length < 2) return
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/products?search=${query}&limit=50`)
      setProducts(response.data.products || [])
    } catch (error) {
      console.error('Error searching products:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCountryToggle = (countryName) => {
    setSelectedCountries(prev => 
      prev.includes(countryName)
        ? prev.filter(c => c !== countryName)
        : [...prev, countryName]
    )
    setSelectAllCountries(false)
  }

  const handleSelectAllCountries = () => {
    if (selectAllCountries) {
      setSelectedCountries([])
    } else {
      setSelectedCountries(countries.map(c => c.name))
    }
    setSelectAllCountries(!selectAllCountries)
  }

  // Gestion des produits et variantes
  const handleProductSelect = (product) => {
    if (!selectedProducts.find(p => p.id === product.id)) {
      setSelectedProducts([...selectedProducts, product])
      setSelectedVariants(prev => ({
        ...prev,
        [product.id]: product.variants.map(v => v.id)
      }))
    }
    setProductSearch('')
    setProducts([])
    setProductMode('selected')
  }

  const handleProductRemove = (productId) => {
    setSelectedProducts(prev => prev.filter(p => p.id !== productId))
    setSelectedVariants(prev => {
      const newVariants = { ...prev }
      delete newVariants[productId]
      return newVariants
    })
    setExpandedProducts(prev => {
      const newExpanded = { ...prev }
      delete newExpanded[productId]
      return newExpanded
    })
  }

  const toggleProductExpanded = (productId) => {
    setExpandedProducts(prev => ({
      ...prev,
      [productId]: !prev[productId]
    }))
  }

  const handleVariantToggle = (productId, variantId) => {
    setSelectedVariants(prev => {
      const current = prev[productId] || []
      if (current.includes(variantId)) {
        return {
          ...prev,
          [productId]: current.filter(id => id !== variantId)
        }
      } else {
        return {
          ...prev,
          [productId]: [...current, variantId]
        }
      }
    })
  }

  const handleSelectAllVariants = (product) => {
    const currentSelected = selectedVariants[product.id] || []
    const allVariantIds = product.variants.map(v => v.id)
    
    if (currentSelected.length === allVariantIds.length) {
      setSelectedVariants(prev => ({
        ...prev,
        [product.id]: []
      }))
    } else {
      setSelectedVariants(prev => ({
        ...prev,
        [product.id]: allVariantIds
      }))
    }
  }

  const getSelectedVariantsCount = (product) => {
    return (selectedVariants[product.id] || []).length
  }

  const handlePreview = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      if (productMode === 'all') {
        setLoadingMessage('Récupération de tous les produits et prix... Cela peut prendre quelques minutes.')
      } else {
        setLoadingMessage('Calcul des prix en cours...')
      }
      
      // Préparer les variantes sélectionnées
      let variantIds = null
      let productIds = null
      
      if (productMode === 'selected' && selectedProducts.length > 0) {
        variantIds = []
        productIds = selectedProducts.map(p => p.id)
        selectedProducts.forEach(product => {
          const productVariants = selectedVariants[product.id] || []
          variantIds.push(...productVariants)
        })
      }
      
      const response = await axios.post(`${API_URL}/pricing/preview`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        product_ids: productIds,
        variant_ids: variantIds,
        all_products: productMode === 'all',
        base_adjustment: settings.baseAdjustment / 100,
        apply_vat: settings.applyVat,
        discount: settings.discount / 100,
        use_market_price: true
      }, {
        timeout: 300000 // 5 min timeout pour gros volumes
      })
      
      setPreview(response.data)
      setShowPreview(true)
      setLoadingMessage('')
    } catch (error) {
      console.error('Preview error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setLoadingMessage('')
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!preview) return
    
    const confirmMessage = `Vous allez modifier ${preview.summary.total_updates} prix sur ${preview.summary.total_countries} marché(s). Continuer ?`
    if (!window.confirm(confirmMessage)) return
    
    // Fonction pour poll la progression
    const pollProgress = async () => {
      try {
        const response = await axios.get(`${API_URL}/pricing/apply-progress`)
        setApplyProgress(response.data)
        return response.data
      } catch (error) {
        console.error('Error fetching progress:', error)
        return null
      }
    }
    
    try {
      setLoading(true)
      setLoadingMessage('Application des modifications en cours...')
      setApplyProgress({ active: true, current_market: 'Démarrage...', markets_done: 0, total_markets: 0 })
      
      let variantIds = null
      let productIds = null
      
      if (productMode === 'selected' && selectedProducts.length > 0) {
        variantIds = []
        productIds = selectedProducts.map(p => p.id)
        selectedProducts.forEach(product => {
          const productVariants = selectedVariants[product.id] || []
          variantIds.push(...productVariants)
        })
      }
      
      // Démarrer le polling de progression
      const progressInterval = setInterval(async () => {
        const progress = await pollProgress()
        if (progress && progress.active) {
          setLoadingMessage(`🔄 ${progress.current_market} (${progress.markets_done}/${progress.total_markets} marchés) - ${progress.variants_updated} variantes`)
        }
      }, 1000)
      
      const response = await axios.post(`${API_URL}/pricing/apply`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        product_ids: productIds,
        variant_ids: variantIds,
        all_products: productMode === 'all',
        base_adjustment: settings.baseAdjustment / 100,
        apply_vat: settings.applyVat,
        discount: settings.discount / 100,
        use_market_price: true,
        dry_run: false
      }, {
        timeout: 600000 // 10 min timeout
      })
      
      // Arrêter le polling
      clearInterval(progressInterval)
      setApplyProgress(null)
      
      if (response.data.results.errors?.length > 0) {
        setMessage({ 
          type: 'warning', 
          text: `${response.data.results.updated_count} prix mis à jour. ${response.data.results.errors.length} erreur(s).`
        })
      } else {
        const cacheMsg = response.data.results.cache_updated ? ` (cache mis à jour)` : ''
        setMessage({ 
          type: 'success', 
          text: `✅ ${response.data.results.updated_count} prix mis à jour avec succès !${cacheMsg}`
        })
      }
      
      setLoadingMessage('')
    } catch (error) {
      console.error('Apply error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setLoadingMessage('')
      setApplyProgress(null)
    } finally {
      setLoading(false)
    }
  }

  // ========================================
  // PROMOS ALÉATOIRES
  // ========================================
  
  const handlePromoPreview = async () => {
    try {
      setLoading(true)
      setLoadingMessage('Génération des promos aléatoires...')
      setMessage(null)
      
      // Générer un seed pour pouvoir reproduire la même sélection
      const newSeed = Math.floor(Math.random() * 1000000)
      setPromoSeed(newSeed)
      
      const response = await axios.post(`${API_URL}/pricing/random-promo/preview`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        catalog_percentage: promoSettings.catalogPercentage,
        min_discount: promoSettings.minDiscount,
        max_discount: promoSettings.maxDiscount,
        seed: newSeed
      })
      
      setPromoPreview(response.data)
      setLoadingMessage('')
    } catch (error) {
      console.error('Promo preview error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setLoadingMessage('')
    } finally {
      setLoading(false)
    }
  }
  
  const handlePromoApply = async () => {
    if (!promoPreview || !promoSeed) return
    
    const confirmMessage = `Vous allez appliquer des promos sur ${promoPreview.summary.products_selected} produits (${promoPreview.summary.total_price_changes} modifications). Continuer ?`
    if (!window.confirm(confirmMessage)) return
    
    // Fonction pour poll la progression
    const pollProgress = async () => {
      try {
        const response = await axios.get(`${API_URL}/pricing/apply-progress`)
        setApplyProgress(response.data)
        return response.data
      } catch (error) {
        return null
      }
    }
    
    try {
      setLoading(true)
      setLoadingMessage('Application des promos en cours...')
      setApplyProgress({ active: true, current_market: 'Démarrage...', markets_done: 0, total_markets: 0 })
      
      // Démarrer le polling
      const progressInterval = setInterval(async () => {
        const progress = await pollProgress()
        if (progress && progress.active) {
          setLoadingMessage(`🎯 ${progress.current_market} (${progress.markets_done}/${progress.total_markets} marchés) - ${progress.variants_updated} variantes`)
        }
      }, 1000)
      
      const response = await axios.post(`${API_URL}/pricing/random-promo/apply`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        catalog_percentage: promoSettings.catalogPercentage,
        min_discount: promoSettings.minDiscount,
        max_discount: promoSettings.maxDiscount,
        seed: promoSeed,
        dry_run: false
      }, {
        timeout: 600000
      })
      
      clearInterval(progressInterval)
      setApplyProgress(null)
      
      if (response.data.results.errors?.length > 0) {
        setMessage({ 
          type: 'warning', 
          text: `${response.data.results.updated_count} prix mis à jour. ${response.data.results.errors.length} erreur(s).`
        })
      } else {
        const cacheMsg = response.data.results.cache_updated ? ` (cache mis à jour)` : ''
        setMessage({ 
          type: 'success', 
          text: `🎉 Promos appliquées ! ${response.data.results.updated_count} prix mis à jour sur ${promoPreview.summary.products_selected} produits${cacheMsg}`
        })
      }
      
      setPromoPreview(null)
      setPromoSeed(null)
      setLoadingMessage('')
    } catch (error) {
      console.error('Promo apply error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setLoadingMessage('')
      setApplyProgress(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-title mb-2">Gestion des Prix</h1>
        <p className="text-luxarmonie-gray-500">
          Modifiez les prix sur vos marchés internationaux
        </p>
      </div>

      {/* Cache Status */}
      <CacheStatus onCacheLoaded={loadCountries} />

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'error' ? 'bg-red-50 text-red-700' : 
          message.type === 'warning' ? 'bg-yellow-50 text-yellow-700' :
          'bg-green-50 text-green-700'
        }`}>
          {message.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <Check className="w-5 h-5" />}
          {message.text}
        </div>
      )}

      {/* Loading overlay */}
      {loading && loadingMessage && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg flex items-center gap-3 text-blue-700">
          <Loader2 className="w-5 h-5 animate-spin" />
          {loadingMessage}
        </div>
      )}

      {/* Sélection Marchés */}
      <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta/10 flex items-center justify-center">
            <Globe className="w-5 h-5 text-luxarmonie-terracotta" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-title">Marchés</h2>
            <p className="text-sm text-luxarmonie-gray-500">
              {selectedCountries.length} marché(s) sélectionné(s)
            </p>
          </div>
        </div>

        {/* Bouton Tous les marchés */}
        <label className="flex items-center gap-3 p-3 bg-luxarmonie-gray-50 rounded-lg cursor-pointer mb-4 hover:bg-luxarmonie-gray-100 transition-colors">
          <input
            type="checkbox"
            checked={selectAllCountries}
            onChange={handleSelectAllCountries}
            className="checkbox-luxarmonie"
          />
          <span className="font-medium">Tous les marchés ({countries.length})</span>
        </label>

        {/* Liste des pays */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-48 overflow-y-auto">
          {countries.map((country) => (
            <label
              key={country.name}
              className={`flex items-center gap-2 p-2 rounded cursor-pointer text-sm transition-colors ${
                selectedCountries.includes(country.name)
                  ? 'bg-luxarmonie-terracotta/10 text-luxarmonie-terracotta'
                  : 'hover:bg-luxarmonie-gray-50'
              }`}
            >
              <input
                type="checkbox"
                checked={selectedCountries.includes(country.name)}
                onChange={() => handleCountryToggle(country.name)}
                className="checkbox-luxarmonie w-4 h-4"
              />
              <span className="truncate">{country.name}</span>
              <span className="text-xs text-luxarmonie-gray-400">{country.currency}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Sélection Produits */}
      <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta/10 flex items-center justify-center">
            <Package className="w-5 h-5 text-luxarmonie-terracotta" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-title">Produits</h2>
            <p className="text-sm text-luxarmonie-gray-500">
              {productMode === 'all' ? 'Tous les produits' : `${selectedProducts.length} produit(s) sélectionné(s)`}
            </p>
          </div>
        </div>

        {/* Mode de sélection */}
        <div className="flex gap-3 mb-4">
          <button
            onClick={() => setProductMode('all')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              productMode === 'all'
                ? 'bg-luxarmonie-terracotta text-white'
                : 'bg-luxarmonie-gray-100 text-luxarmonie-gray-700 hover:bg-luxarmonie-gray-200'
            }`}
          >
            <Database className="w-4 h-4" />
            Tous les produits
          </button>
          <button
            onClick={() => setProductMode('selected')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              productMode === 'selected'
                ? 'bg-luxarmonie-terracotta text-white'
                : 'bg-luxarmonie-gray-100 text-luxarmonie-gray-700 hover:bg-luxarmonie-gray-200'
            }`}
          >
            <Search className="w-4 h-4" />
            Sélection manuelle
          </button>
        </div>

        {/* Avertissement tous les produits */}
        {productMode === 'all' && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
            <p className="text-sm text-yellow-800">
              <strong>⚠️ Attention :</strong> Cette action concernera tous vos produits (~1200+). 
              La récupération des prix peut prendre plusieurs minutes.
            </p>
          </div>
        )}

        {/* Recherche de produits (mode sélection) */}
        {productMode === 'selected' && (
          <>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-luxarmonie-gray-400" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => {
                  setProductSearch(e.target.value)
                  if (e.target.value.length >= 2) {
                    searchProducts(e.target.value)
                  }
                }}
                placeholder="Rechercher un produit..."
                className="w-full pl-10 pr-4 py-3 border border-luxarmonie-gray-200 rounded-lg"
              />
              {loading && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 animate-spin text-luxarmonie-gray-400" />
              )}
            </div>

            {/* Résultats de recherche */}
            {products.length > 0 && (
              <div className="mb-4 border border-luxarmonie-gray-200 rounded-lg max-h-60 overflow-y-auto">
                {products.map((product) => (
                  <button
                    key={product.id}
                    onClick={() => handleProductSelect(product)}
                    className="w-full flex items-center gap-3 p-3 hover:bg-luxarmonie-gray-50 transition-colors border-b border-luxarmonie-gray-100 last:border-0"
                  >
                    {product.featuredImage?.url && (
                      <img src={product.featuredImage.url} alt="" className="w-10 h-10 object-cover rounded" />
                    )}
                    <div className="flex-1 text-left">
                      <p className="font-medium text-sm">{product.title}</p>
                      <p className="text-xs text-luxarmonie-gray-500">{product.variants.length} variante(s)</p>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Produits sélectionnés */}
            {selectedProducts.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-luxarmonie-gray-700 mb-2">
                  Produits sélectionnés :
                </p>
                {selectedProducts.map((product) => (
                  <div key={product.id} className="border border-luxarmonie-gray-200 rounded-lg overflow-hidden">
                    {/* Product Header */}
                    <div className="flex items-center gap-3 p-3 bg-luxarmonie-gray-50">
                      <button
                        onClick={() => toggleProductExpanded(product.id)}
                        className="text-luxarmonie-gray-500 hover:text-luxarmonie-black transition-colors"
                      >
                        {expandedProducts[product.id] ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </button>
                      
                      {product.featuredImage?.url && (
                        <img src={product.featuredImage.url} alt="" className="w-10 h-10 object-cover rounded" />
                      )}
                      
                      <div className="flex-1">
                        <p className="font-medium text-sm">{product.title}</p>
                        <p className="text-xs text-luxarmonie-gray-500">
                          {getSelectedVariantsCount(product)}/{product.variants.length} variante(s)
                        </p>
                      </div>
                      
                      <button
                        onClick={() => handleProductRemove(product.id)}
                        className="text-luxarmonie-gray-400 hover:text-red-500 transition-colors text-lg"
                      >
                        ×
                      </button>
                    </div>
                    
                    {/* Variants List (Expanded) */}
                    {expandedProducts[product.id] && (
                      <div className="p-3 space-y-1 border-t border-luxarmonie-gray-100">
                        <label className="flex items-center gap-2 p-2 bg-luxarmonie-gray-50 rounded cursor-pointer hover:bg-luxarmonie-gray-100 transition-colors mb-2">
                          <input
                            type="checkbox"
                            checked={(selectedVariants[product.id] || []).length === product.variants.length}
                            onChange={() => handleSelectAllVariants(product)}
                            className="checkbox-luxarmonie w-4 h-4"
                          />
                          <span className="text-sm font-medium">Toutes les variantes</span>
                        </label>
                        
                        {product.variants.map((variant) => (
                          <label
                            key={variant.id}
                            className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                              (selectedVariants[product.id] || []).includes(variant.id)
                                ? 'bg-luxarmonie-terracotta/5'
                                : 'hover:bg-luxarmonie-gray-50'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={(selectedVariants[product.id] || []).includes(variant.id)}
                              onChange={() => handleVariantToggle(product.id, variant.id)}
                              className="checkbox-luxarmonie w-4 h-4"
                            />
                            <span className="flex-1 text-sm truncate">{variant.title}</span>
                            <span className="text-sm text-luxarmonie-gray-500">{variant.price}€</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Paramètres */}
      <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 mb-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta/10 flex items-center justify-center">
            <Settings2 className="w-5 h-5 text-luxarmonie-terracotta" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-title">Paramètres</h2>
            <p className="text-sm text-luxarmonie-gray-500">Configurez les règles de pricing</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Base Adjustment */}
          <div>
            <label className="block text-sm font-medium text-luxarmonie-gray-700 mb-2">
              Ajustement de prix
            </label>
            <div className="relative">
              <input
                type="number"
                value={settings.baseAdjustment}
                onChange={(e) => setSettings({ ...settings, baseAdjustment: parseFloat(e.target.value) || 0 })}
                className="w-full px-4 py-3 border border-luxarmonie-gray-200 rounded-lg pr-8"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-luxarmonie-gray-500">%</span>
            </div>
            <p className="text-xs text-luxarmonie-gray-400 mt-1">
              Appliqué sur le prix actuel du marché
            </p>
          </div>

          {/* Discount */}
          <div>
            <label className="block text-sm font-medium text-luxarmonie-gray-700 mb-2">
              Réduction affichée
            </label>
            <div className="relative">
              <input
                type="number"
                value={settings.discount}
                onChange={(e) => setSettings({ ...settings, discount: parseFloat(e.target.value) || 0 })}
                className="w-full px-4 py-3 border border-luxarmonie-gray-200 rounded-lg pr-8"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-luxarmonie-gray-500">%</span>
            </div>
            <p className="text-xs text-luxarmonie-gray-400 mt-1">
              Compare At calculé pour cette réduction
            </p>
          </div>

          {/* Apply VAT */}
          <div>
            <label className="block text-sm font-medium text-luxarmonie-gray-700 mb-2">
              TVA par pays
            </label>
            <label className="flex items-center gap-3 p-3 bg-luxarmonie-gray-50 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={settings.applyVat}
                onChange={(e) => setSettings({ ...settings, applyVat: e.target.checked })}
                className="checkbox-luxarmonie"
              />
              <span>Appliquer la TVA automatiquement</span>
            </label>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={handlePreview}
          disabled={loading || (selectedCountries.length === 0 && !selectAllCountries)}
          className="flex items-center gap-2 px-6 py-3 bg-luxarmonie-gray-100 text-luxarmonie-black rounded-lg font-medium hover:bg-luxarmonie-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Eye className="w-5 h-5" />}
          Prévisualiser
        </button>
        
        <button
          onClick={handleApply}
          disabled={loading || !preview || (selectedCountries.length === 0 && !selectAllCountries)}
          className="flex items-center gap-2 px-6 py-3 bg-luxarmonie-terracotta text-white rounded-lg font-medium hover:bg-luxarmonie-terracotta-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
          Appliquer les modifications
        </button>
      </div>

      {/* ========================================
          MODULE PROMOS ALÉATOIRES
          ======================================== */}
      <div className="mt-8 bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl border border-purple-200 p-6">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setShowPromoModule(!showPromoModule)}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-title text-purple-900">🎯 Promos Aléatoires</h2>
              <p className="text-sm text-purple-600">
                Générez des promotions sur une partie de votre catalogue
              </p>
            </div>
          </div>
          <ChevronDown className={`w-5 h-5 text-purple-400 transition-transform ${showPromoModule ? 'rotate-180' : ''}`} />
        </div>

        {showPromoModule && (
          <div className="mt-6 space-y-6">
            {/* Paramètres */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* % du catalogue */}
              <div className="bg-white rounded-xl p-4 shadow-sm">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Percent className="w-4 h-4 inline mr-1" />
                  % du catalogue en promo
                </label>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  value={promoSettings.catalogPercentage}
                  onChange={(e) => setPromoSettings(prev => ({ ...prev, catalogPercentage: parseInt(e.target.value) }))}
                  className="w-full h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between mt-2">
                  <span className="text-xs text-gray-500">10%</span>
                  <span className="text-lg font-bold text-purple-600">{promoSettings.catalogPercentage}%</span>
                  <span className="text-xs text-gray-500">100%</span>
                </div>
              </div>

              {/* Réduction min */}
              <div className="bg-white rounded-xl p-4 shadow-sm">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Réduction minimum
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="5"
                    max={promoSettings.maxDiscount - 5}
                    value={promoSettings.minDiscount}
                    onChange={(e) => setPromoSettings(prev => ({ ...prev, minDiscount: parseInt(e.target.value) || 5 }))}
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                  <span className="text-gray-500 font-medium">%</span>
                </div>
              </div>

              {/* Réduction max */}
              <div className="bg-white rounded-xl p-4 shadow-sm">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Réduction maximum
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={promoSettings.minDiscount + 5}
                    max="80"
                    value={promoSettings.maxDiscount}
                    onChange={(e) => setPromoSettings(prev => ({ ...prev, maxDiscount: parseInt(e.target.value) || 40 }))}
                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                  <span className="text-gray-500 font-medium">%</span>
                </div>
              </div>
            </div>

            {/* Info */}
            <div className="bg-purple-100 rounded-lg p-4 text-sm text-purple-800">
              <strong>💡 Comment ça marche :</strong>
              <ul className="mt-2 space-y-1 list-disc list-inside">
                <li><strong>{promoSettings.catalogPercentage}%</strong> de vos produits seront sélectionnés au hasard</li>
                <li>Chaque produit recevra une réduction entre <strong>{promoSettings.minDiscount}%</strong> et <strong>{promoSettings.maxDiscount}%</strong></li>
                <li>Toutes les variantes d'un produit ont la même réduction</li>
                <li>Les prix actuels deviennent les prix barrés (Compare At)</li>
              </ul>
            </div>

            {/* Boutons */}
            <div className="flex items-center gap-4">
              <button
                onClick={handlePromoPreview}
                disabled={loading || (selectedCountries.length === 0 && !selectAllCountries)}
                className="flex items-center gap-2 px-6 py-3 bg-purple-100 text-purple-700 rounded-lg font-medium hover:bg-purple-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Eye className="w-5 h-5" />}
                Générer les promos
              </button>
              
              <button
                onClick={handlePromoApply}
                disabled={loading || !promoPreview}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                Appliquer les promos
              </button>
            </div>

            {/* Preview des promos */}
            {promoPreview && (
              <div className="bg-white rounded-xl p-6 shadow-sm border border-purple-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-purple-900">
                    🎲 Sélection aléatoire générée
                  </h3>
                  <button
                    onClick={() => { setPromoPreview(null); setPromoSeed(null); }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </div>

                {/* Résumé */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-purple-50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-purple-600">{promoPreview.summary.products_selected}</div>
                    <div className="text-xs text-purple-500">Produits en promo</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-purple-600">{promoPreview.summary.total_products_in_catalog}</div>
                    <div className="text-xs text-purple-500">Total catalogue</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-purple-600">{promoPreview.summary.total_markets}</div>
                    <div className="text-xs text-purple-500">Marchés</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-purple-600">{promoPreview.summary.total_price_changes}</div>
                    <div className="text-xs text-purple-500">Modifications</div>
                  </div>
                </div>

                {/* Liste des produits sélectionnés */}
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Produits sélectionnés :</h4>
                  <div className="max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {promoPreview.products?.slice(0, 50).map((product, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-white rounded px-3 py-2 text-sm">
                          <span className="truncate flex-1" title={product.title}>{product.title}</span>
                          <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                            -{product.discount}%
                          </span>
                        </div>
                      ))}
                    </div>
                    {promoPreview.products?.length > 50 && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        Et {promoPreview.products.length - 50} autres produits...
                      </p>
                    )}
                  </div>
                </div>

                {/* Aperçu des prix */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Aperçu des modifications :</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2 px-3">Produit</th>
                          <th className="text-left py-2 px-3">Marché</th>
                          <th className="text-right py-2 px-3">Ancien prix</th>
                          <th className="text-right py-2 px-3">Nouveau prix</th>
                          <th className="text-right py-2 px-3">Réduction</th>
                        </tr>
                      </thead>
                      <tbody>
                        {promoPreview.preview?.slice(0, 20).map((row, idx) => (
                          <tr key={idx} className="border-b border-gray-100">
                            <td className="py-2 px-3 truncate max-w-[200px]" title={row.product_title}>{row.product_title}</td>
                            <td className="py-2 px-3">{row.country}</td>
                            <td className="py-2 px-3 text-right text-gray-500 line-through">{row.current_price} {row.currency}</td>
                            <td className="py-2 px-3 text-right font-medium text-green-600">{row.new_price} {row.currency}</td>
                            <td className="py-2 px-3 text-right">
                              <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                                -{row.discount_percentage}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {promoPreview.preview?.length > 20 && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        Et {promoPreview.preview.length - 20} autres modifications...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Preview Panel */}
      {showPreview && preview && (
        <div className="mt-8 bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 animate-fadeIn">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold tracking-title">Prévisualisation</h2>
              <p className="text-sm text-luxarmonie-gray-500">
                {preview.summary.total_updates} modifications sur {preview.summary.total_countries} marché(s)
                {preview.summary.markets_with_prices !== undefined && (
                  <span className="ml-2 text-green-600">
                    ({preview.summary.markets_with_prices} marchés avec prix actuels)
                  </span>
                )}
              </p>
            </div>
            <button
              onClick={() => setShowPreview(false)}
              className="text-luxarmonie-gray-400 hover:text-luxarmonie-black transition-colors text-2xl"
            >
              ×
            </button>
          </div>

          {/* Preview Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-luxarmonie-gray-100">
                  <th className="text-left py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Produit</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Marché</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Prix actuel</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Nouveau prix</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Compare At</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-luxarmonie-gray-500">Réduction</th>
                </tr>
              </thead>
              <tbody>
                {preview.preview.slice(0, 100).map((row, index) => (
                  <tr key={index} className="border-b border-luxarmonie-gray-50 hover:bg-luxarmonie-gray-50">
                    <td className="py-3 px-4 text-sm">{row.title || row.sku}</td>
                    <td className="py-3 px-4 text-sm">{row.country}</td>
                    <td className="py-3 px-4 text-sm text-right text-luxarmonie-gray-500">
                      {row.current_price != null 
                        ? <span className="text-green-600 font-medium">{row.current_price} {row.currency}</span>
                        : <span className="text-gray-300 italic">Non défini</span>
                      }
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-medium">
                      {row.new_price} {row.currency}
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-luxarmonie-gray-500">
                      {row.compare_at_price} {row.currency}
                    </td>
                    <td className="py-3 px-4 text-sm text-right">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        row.discount_percentage > 0 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        -{row.discount_percentage}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {preview.preview.length > 100 && (
            <p className="text-sm text-luxarmonie-gray-500 mt-4 text-center">
              Et {preview.preview.length - 100} autres modifications...
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default PricingModule
