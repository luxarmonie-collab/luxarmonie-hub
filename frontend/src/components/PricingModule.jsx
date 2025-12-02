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
  Loader2,
  RefreshCw
} from 'lucide-react'
import axios from 'axios'

const API_URL = '/api'

function PricingModule() {
  // États
  const [loading, setLoading] = useState(false)
  const [countries, setCountries] = useState([])
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectAllCountries, setSelectAllCountries] = useState(false)
  const [products, setProducts] = useState([])
  const [selectedProducts, setSelectedProducts] = useState([])
  const [selectAllProducts, setSelectAllProducts] = useState(true)
  const [productSearch, setProductSearch] = useState('')
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [showProductDropdown, setShowProductDropdown] = useState(false)
  
  // Paramètres de pricing
  const [settings, setSettings] = useState({
    baseAdjustment: -12,  // -12%
    applyVat: true,
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
      // Fallback avec données locales si API non dispo
      setCountries([
        { name: 'France', currency: 'EUR', vat: 0.19 },
        { name: 'Allemagne', currency: 'EUR', vat: 0.19 },
        { name: 'USA', currency: 'USD', vat: 0 },
        { name: 'UK', currency: 'GBP', vat: 0 },
        // ... autres pays
      ])
    }
  }

  const searchProducts = async (query) => {
    if (query.length < 2) return
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/products?search=${query}&limit=20`)
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

  const handlePreview = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const response = await axios.post(`${API_URL}/pricing/preview`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        product_ids: selectAllProducts ? null : selectedProducts.map(p => p.id),
        base_adjustment: settings.baseAdjustment / 100,
        apply_vat: settings.applyVat,
        discount: settings.discount / 100
      })
      
      setPreview(response.data)
      setShowPreview(true)
    } catch (error) {
      setMessage({ type: 'error', text: 'Erreur lors de la prévisualisation' })
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    try {
      setLoading(true)
      setMessage(null)
      
      const response = await axios.post(`${API_URL}/pricing/apply`, {
        countries: selectAllCountries ? ['all'] : selectedCountries,
        product_ids: selectAllProducts ? null : selectedProducts.map(p => p.id),
        base_adjustment: settings.baseAdjustment / 100,
        apply_vat: settings.applyVat,
        discount: settings.discount / 100,
        dry_run: false
      })
      
      setMessage({ 
        type: 'success', 
        text: `Prix mis à jour pour ${response.data.results.success.length} marchés` 
      })
      setShowPreview(false)
    } catch (error) {
      setMessage({ type: 'error', text: 'Erreur lors de l\'application des prix' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fadeIn">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-title text-luxarmonie-black">
          Modification de Prix
        </h1>
        <p className="text-luxarmonie-gray-500 mt-2 tracking-body">
          Modifiez les prix de vos produits sur tous les marchés en quelques clics
        </p>
      </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message.type === 'success' ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <p>{message.text}</p>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        
        {/* Sélection Pays */}
        <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta/10 flex items-center justify-center">
              <Globe className="w-5 h-5 text-luxarmonie-terracotta" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-title">Marchés</h2>
              <p className="text-sm text-luxarmonie-gray-500">Sélectionnez les pays ciblés</p>
            </div>
          </div>

          {/* Toggle All */}
          <label className="flex items-center gap-3 p-3 bg-luxarmonie-gray-50 rounded-lg mb-4 cursor-pointer hover:bg-luxarmonie-gray-100 transition-colors">
            <input
              type="checkbox"
              checked={selectAllCountries}
              onChange={handleSelectAllCountries}
              className="checkbox-luxarmonie"
            />
            <span className="font-medium">Tous les marchés</span>
            <span className="ml-auto text-sm text-luxarmonie-gray-500">
              {countries.length} pays
            </span>
          </label>

          {/* Countries List */}
          <div className="max-h-64 overflow-y-auto space-y-1">
            {countries.map((country) => (
              <label
                key={country.name}
                className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedCountries.includes(country.name)
                    ? 'bg-luxarmonie-terracotta/10'
                    : 'hover:bg-luxarmonie-gray-50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedCountries.includes(country.name)}
                  onChange={() => handleCountryToggle(country.name)}
                  disabled={selectAllCountries}
                  className="checkbox-luxarmonie"
                />
                <span className="flex-1">{country.name}</span>
                <span className="text-sm text-luxarmonie-gray-400">
                  {country.currency}
                </span>
                {country.vat > 0 && (
                  <span className="text-xs bg-luxarmonie-gray-100 px-2 py-0.5 rounded">
                    TVA {(country.vat * 100).toFixed(0)}%
                  </span>
                )}
              </label>
            ))}
          </div>

          {/* Selection Count */}
          <div className="mt-4 pt-4 border-t border-luxarmonie-gray-100">
            <p className="text-sm text-luxarmonie-gray-500">
              {selectAllCountries 
                ? `${countries.length} marchés sélectionnés`
                : `${selectedCountries.length} marché(s) sélectionné(s)`
              }
            </p>
          </div>
        </div>

        {/* Sélection Produits */}
        <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta/10 flex items-center justify-center">
              <Package className="w-5 h-5 text-luxarmonie-terracotta" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-title">Produits</h2>
              <p className="text-sm text-luxarmonie-gray-500">Tous ou sélection spécifique</p>
            </div>
          </div>

          {/* Toggle All Products */}
          <label className="flex items-center gap-3 p-3 bg-luxarmonie-gray-50 rounded-lg mb-4 cursor-pointer hover:bg-luxarmonie-gray-100 transition-colors">
            <input
              type="checkbox"
              checked={selectAllProducts}
              onChange={() => setSelectAllProducts(!selectAllProducts)}
              className="checkbox-luxarmonie"
            />
            <span className="font-medium">Tous les produits</span>
          </label>

          {/* Search Products */}
          {!selectAllProducts && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-luxarmonie-gray-400" />
              <input
                type="text"
                placeholder="Rechercher un produit (titre, SKU)..."
                value={productSearch}
                onChange={(e) => {
                  setProductSearch(e.target.value)
                  searchProducts(e.target.value)
                }}
                className="w-full pl-10 pr-4 py-3 border border-luxarmonie-gray-200 rounded-lg focus:ring-2 focus:ring-luxarmonie-terracotta focus:border-transparent"
              />
              
              {/* Results */}
              {products.length > 0 && productSearch && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-lg shadow-lg border border-luxarmonie-gray-200 max-h-64 overflow-y-auto z-10">
                  {products.map((product) => (
                    <button
                      key={product.id}
                      onClick={() => {
                        if (!selectedProducts.find(p => p.id === product.id)) {
                          setSelectedProducts([...selectedProducts, product])
                        }
                        setProductSearch('')
                        setProducts([])
                      }}
                      className="w-full flex items-center gap-3 p-3 hover:bg-luxarmonie-gray-50 transition-colors text-left"
                    >
                      {product.image && (
                        <img src={product.image} alt="" className="w-10 h-10 rounded object-cover" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{product.title}</p>
                        <p className="text-sm text-luxarmonie-gray-500">
                          {product.variantsCount} variante(s)
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Selected Products */}
          {!selectAllProducts && selectedProducts.length > 0 && (
            <div className="mt-4 space-y-2">
              {selectedProducts.map((product) => (
                <div key={product.id} className="flex items-center gap-3 p-2 bg-luxarmonie-gray-50 rounded-lg">
                  <span className="flex-1 truncate">{product.title}</span>
                  <button
                    onClick={() => setSelectedProducts(prev => prev.filter(p => p.id !== product.id))}
                    className="text-luxarmonie-gray-400 hover:text-red-500 transition-colors"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
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
              Ajustement de base
            </label>
            <div className="relative">
              <input
                type="number"
                value={settings.baseAdjustment}
                onChange={(e) => setSettings({ ...settings, baseAdjustment: parseFloat(e.target.value) })}
                className="w-full px-4 py-3 border border-luxarmonie-gray-200 rounded-lg pr-8"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-luxarmonie-gray-500">%</span>
            </div>
            <p className="text-xs text-luxarmonie-gray-400 mt-1">
              Appliqué avant TVA (-12% = prix HT)
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
                onChange={(e) => setSettings({ ...settings, discount: parseFloat(e.target.value) })}
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
                {preview.summary.total_updates} modifications sur {preview.summary.total_countries} marchés
              </p>
            </div>
            <button
              onClick={() => setShowPreview(false)}
              className="text-luxarmonie-gray-400 hover:text-luxarmonie-black transition-colors"
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
                {preview.preview.slice(0, 50).map((row, index) => (
                  <tr key={index} className="border-b border-luxarmonie-gray-50 hover:bg-luxarmonie-gray-50">
                    <td className="py-3 px-4 text-sm">{row.title || row.sku}</td>
                    <td className="py-3 px-4 text-sm">{row.country}</td>
                    <td className="py-3 px-4 text-sm text-right text-luxarmonie-gray-500">
                      {row.original_eur}€
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-medium">
                      {row.final_price} {row.currency}
                    </td>
                    <td className="py-3 px-4 text-sm text-right text-luxarmonie-gray-500">
                      {row.compare_at} {row.currency}
                    </td>
                    <td className="py-3 px-4 text-sm text-right">
                      <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                        -{row.discount}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {preview.preview.length > 50 && (
            <p className="text-sm text-luxarmonie-gray-500 mt-4 text-center">
              Et {preview.preview.length - 50} autres modifications...
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default PricingModule
