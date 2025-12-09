import { useState, useEffect } from 'react'
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
  Database
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

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
    
    try {
      setLoading(true)
      setLoadingMessage('Application des modifications en cours...')
      
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
      
      if (response.data.results.errors?.length > 0) {
        setMessage({ 
          type: 'warning', 
          text: `${response.data.results.updated_count} prix mis à jour. ${response.data.results.errors.length} erreur(s).`
        })
      } else {
        setMessage({ 
          type: 'success', 
          text: `✅ ${response.data.results.updated_count} prix mis à jour avec succès !`
        })
      }
      
      setLoadingMessage('')
    } catch (error) {
      console.error('Apply error:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setLoadingMessage('')
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
