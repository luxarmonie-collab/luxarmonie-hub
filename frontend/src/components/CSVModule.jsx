import { useState } from 'react'
import { 
  Upload, 
  Download, 
  FileSpreadsheet, 
  Percent, 
  Sparkles,
  Loader2,
  Check,
  AlertCircle,
  Trash2,
  RefreshCw
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api'

function CSVModule() {
  // État du fichier
  const [file, setFile] = useState(null)
  const [fileInfo, setFileInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  
  // Mode de modification
  const [mode, setMode] = useState('adjustment') // 'adjustment', 'promo', 'remove'
  
  // Paramètres ajustement
  const [adjustment, setAdjustment] = useState(0)
  const [compareAt, setCompareAt] = useState(40)
  
  // Paramètres promos
  const [promoCatalog, setPromoCatalog] = useState(50)
  const [promoMin, setPromoMin] = useState(10)
  const [promoMax, setPromoMax] = useState(40)

  // Upload et analyse du fichier
  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0]
    if (!selectedFile) return
    
    setFile(selectedFile)
    setMessage(null)
    setLoading(true)
    
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      
      const response = await axios.post(`${API_URL}/csv/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      setFileInfo(response.data)
      setMessage({ type: 'success', text: `✅ Fichier analysé: ${response.data.variants_count} variantes, ${response.data.countries_count} pays` })
    } catch (error) {
      console.error('Error analyzing file:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
      setFileInfo(null)
    } finally {
      setLoading(false)
    }
  }

  // Traitement et téléchargement
  const handleProcess = async () => {
    if (!file) return
    
    setLoading(true)
    setMessage(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('adjustment', mode === 'adjustment' ? adjustment : 0)
      formData.append('compare_at', compareAt)
      formData.append('promo_mode', mode === 'promo')
      formData.append('promo_catalog', promoCatalog)
      formData.append('promo_min', promoMin)
      formData.append('promo_max', promoMax)
      formData.append('remove_promos', mode === 'remove')
      
      const response = await axios.post(`${API_URL}/csv/process`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
      })
      
      // Télécharger le fichier
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      
      // Extraire le nom du fichier depuis les headers
      const contentDisposition = response.headers['content-disposition']
      let filename = 'prix_modifies.csv'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/)
        if (match) filename = match[1]
      }
      
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      setMessage({ type: 'success', text: `✅ Fichier téléchargé: ${filename}` })
    } catch (error) {
      console.error('Error processing file:', error)
      setMessage({ type: 'error', text: `Erreur: ${error.response?.data?.detail || error.message}` })
    } finally {
      setLoading(false)
    }
  }

  // Reset
  const handleReset = () => {
    setFile(null)
    setFileInfo(null)
    setMessage(null)
    setAdjustment(0)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-title mb-2">📊 Modification CSV Matrixify</h1>
        <p className="text-luxarmonie-gray-500">
          Modifiez vos prix en masse via CSV - Import/Export rapide (~10 min pour 800K prix)
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

      {/* Zone d'upload */}
      <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">1. Upload CSV Matrixify</h2>
            <p className="text-sm text-luxarmonie-gray-500">
              Export depuis Shopify avec les prix par marché
            </p>
          </div>
        </div>

        {!file ? (
          <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-luxarmonie-gray-300 rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
            <Upload className="w-10 h-10 text-luxarmonie-gray-400 mb-2" />
            <span className="text-luxarmonie-gray-600 font-medium">Cliquez pour sélectionner un CSV</span>
            <span className="text-sm text-luxarmonie-gray-400">ou glissez-déposez</span>
            <input 
              type="file" 
              accept=".csv"
              onChange={handleFileChange}
              className="hidden" 
            />
          </label>
        ) : (
          <div className="bg-luxarmonie-gray-50 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="w-8 h-8 text-green-600" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  {fileInfo && (
                    <p className="text-sm text-luxarmonie-gray-500">
                      {fileInfo.variants_count} variantes • {fileInfo.countries_count} pays
                    </p>
                  )}
                </div>
              </div>
              <button 
                onClick={handleReset}
                className="p-2 hover:bg-luxarmonie-gray-200 rounded-lg transition-colors"
              >
                <Trash2 className="w-5 h-5 text-luxarmonie-gray-400" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Options de modification */}
      {fileInfo && (
        <>
          <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                <Percent className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">2. Type de modification</h2>
                <p className="text-sm text-luxarmonie-gray-500">
                  Choisissez comment modifier les prix
                </p>
              </div>
            </div>

            {/* Sélection du mode */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <button
                onClick={() => setMode('adjustment')}
                className={`p-4 rounded-xl border-2 transition-colors ${
                  mode === 'adjustment' 
                    ? 'border-purple-500 bg-purple-50' 
                    : 'border-luxarmonie-gray-200 hover:border-purple-300'
                }`}
              >
                <Percent className={`w-6 h-6 mx-auto mb-2 ${mode === 'adjustment' ? 'text-purple-600' : 'text-luxarmonie-gray-400'}`} />
                <p className="font-medium">Ajustement Global</p>
                <p className="text-xs text-luxarmonie-gray-500">+/- % sur tous les prix</p>
              </button>

              <button
                onClick={() => setMode('promo')}
                className={`p-4 rounded-xl border-2 transition-colors ${
                  mode === 'promo' 
                    ? 'border-purple-500 bg-purple-50' 
                    : 'border-luxarmonie-gray-200 hover:border-purple-300'
                }`}
              >
                <Sparkles className={`w-6 h-6 mx-auto mb-2 ${mode === 'promo' ? 'text-purple-600' : 'text-luxarmonie-gray-400'}`} />
                <p className="font-medium">Promos Aléatoires</p>
                <p className="text-xs text-luxarmonie-gray-500">Réductions variées</p>
              </button>

              <button
                onClick={() => setMode('remove')}
                className={`p-4 rounded-xl border-2 transition-colors ${
                  mode === 'remove' 
                    ? 'border-purple-500 bg-purple-50' 
                    : 'border-luxarmonie-gray-200 hover:border-purple-300'
                }`}
              >
                <RefreshCw className={`w-6 h-6 mx-auto mb-2 ${mode === 'remove' ? 'text-purple-600' : 'text-luxarmonie-gray-400'}`} />
                <p className="font-medium">Supprimer Promos</p>
                <p className="text-xs text-luxarmonie-gray-500">Retour prix normal</p>
              </button>
            </div>

            {/* Paramètres selon le mode */}
            {mode === 'adjustment' && (
              <div className="space-y-4 bg-luxarmonie-gray-50 rounded-xl p-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Ajustement des prix (%)
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="-50"
                      max="100"
                      value={adjustment}
                      onChange={(e) => setAdjustment(parseInt(e.target.value))}
                      className="flex-1 h-2 bg-luxarmonie-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={adjustment}
                        onChange={(e) => setAdjustment(parseInt(e.target.value) || 0)}
                        className="w-20 px-3 py-2 border border-luxarmonie-gray-200 rounded-lg text-center font-bold"
                      />
                      <span className="text-lg font-bold">%</span>
                    </div>
                  </div>
                  <p className="text-sm text-luxarmonie-gray-500 mt-2">
                    {adjustment > 0 ? `+${adjustment}% = Augmentation` : adjustment < 0 ? `${adjustment}% = Réduction` : 'Aucun changement'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Compare-at (prix barré) : +{compareAt}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="80"
                    value={compareAt}
                    onChange={(e) => setCompareAt(parseInt(e.target.value))}
                    className="w-full h-2 bg-luxarmonie-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <p className="text-sm text-luxarmonie-gray-500 mt-1">
                    Le prix barré sera {compareAt}% plus haut que le nouveau prix
                  </p>
                </div>
              </div>
            )}

            {mode === 'promo' && (
              <div className="space-y-4 bg-purple-50 rounded-xl p-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    % du catalogue en promo
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="5"
                      value={promoCatalog}
                      onChange={(e) => setPromoCatalog(parseInt(e.target.value))}
                      className="flex-1 h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-xl font-bold text-purple-600 w-16 text-right">{promoCatalog}%</span>
                  </div>
                  <p className="text-sm text-purple-600 mt-1">
                    ≈ {Math.round(fileInfo.variants_count * promoCatalog / 100)} variantes sur {fileInfo.variants_count}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Réduction min</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="5"
                        max={promoMax - 5}
                        value={promoMin}
                        onChange={(e) => setPromoMin(parseInt(e.target.value) || 5)}
                        className="flex-1 px-3 py-2 border border-purple-200 rounded-lg"
                      />
                      <span>%</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Réduction max</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min={promoMin + 5}
                        max="80"
                        value={promoMax}
                        onChange={(e) => setPromoMax(parseInt(e.target.value) || 40)}
                        className="flex-1 px-3 py-2 border border-purple-200 rounded-lg"
                      />
                      <span>%</span>
                    </div>
                  </div>
                </div>

                <div className="bg-purple-100 rounded-lg p-3 text-sm text-purple-800">
                  💡 Chaque produit recevra une réduction aléatoire entre -{promoMin}% et -{promoMax}%
                </div>
              </div>
            )}

            {mode === 'remove' && (
              <div className="bg-orange-50 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <RefreshCw className="w-6 h-6 text-orange-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-orange-800">Suppression des promos</p>
                    <p className="text-sm text-orange-600 mt-1">
                      Le prix Compare-at devient le nouveau prix, et le Compare-at est vidé.
                      Utile pour revenir aux prix normaux après les soldes.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bouton de traitement */}
          <div className="bg-white rounded-2xl border border-luxarmonie-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                <Download className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">3. Générer et télécharger</h2>
                <p className="text-sm text-luxarmonie-gray-500">
                  Le fichier CSV modifié sera prêt à importer dans Matrixify
                </p>
              </div>
            </div>

            <button
              onClick={handleProcess}
              disabled={loading || !file}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Traitement en cours...
                </>
              ) : (
                <>
                  <Download className="w-5 h-5" />
                  Télécharger le CSV modifié
                </>
              )}
            </button>

            {/* Résumé */}
            <div className="mt-4 p-4 bg-luxarmonie-gray-50 rounded-lg text-sm">
              <p className="font-medium mb-2">📋 Résumé de la modification :</p>
              <ul className="space-y-1 text-luxarmonie-gray-600">
                <li>• {fileInfo.variants_count} variantes × {fileInfo.countries_count} pays = <strong>{(fileInfo.variants_count * fileInfo.countries_count).toLocaleString()}</strong> prix</li>
                {mode === 'adjustment' && adjustment !== 0 && (
                  <li>• Ajustement : <strong>{adjustment > 0 ? '+' : ''}{adjustment}%</strong></li>
                )}
                {mode === 'adjustment' && (
                  <li>• Compare-at : <strong>+{compareAt}%</strong> du nouveau prix</li>
                )}
                {mode === 'promo' && (
                  <>
                    <li>• {promoCatalog}% du catalogue en promo</li>
                    <li>• Réductions entre <strong>-{promoMin}%</strong> et <strong>-{promoMax}%</strong></li>
                  </>
                )}
                {mode === 'remove' && (
                  <li>• Suppression de toutes les promos</li>
                )}
                <li>• ✅ Terminaisons psychologiques automatiques</li>
              </ul>
            </div>
          </div>
        </>
      )}

      {/* Instructions */}
      <div className="mt-8 bg-blue-50 rounded-xl p-6">
        <h3 className="font-semibold text-blue-900 mb-3">📖 Comment ça marche</h3>
        <ol className="space-y-2 text-sm text-blue-800">
          <li><strong>1.</strong> Exportez vos prix depuis Shopify avec Matrixify (format "Variant ID + Prix par marché")</li>
          <li><strong>2.</strong> Uploadez le CSV ici</li>
          <li><strong>3.</strong> Configurez la modification (+X%, promos, etc.)</li>
          <li><strong>4.</strong> Téléchargez le CSV modifié</li>
          <li><strong>5.</strong> Importez-le dans Matrixify → <strong>~10 min</strong> pour tout le catalogue !</li>
        </ol>
        <div className="mt-4 p-3 bg-blue-100 rounded-lg">
          <p className="text-sm text-blue-900">
            💡 <strong>Avantage :</strong> Via CSV c'est 100x plus rapide que via l'API Shopify !
          </p>
        </div>
      </div>
    </div>
  )
}

export default CSVModule
