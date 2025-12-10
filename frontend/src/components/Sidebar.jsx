import { 
  Tag, 
  LayoutDashboard, 
  Package, 
  Settings, 
  ChevronRight,
  Sparkles,
  FileSpreadsheet
} from 'lucide-react'

const menuItems = [
  {
    id: 'pricing',
    label: 'Modification de Prix',
    icon: Tag,
    active: true
  },
  {
    id: 'csv',
    label: 'Import/Export CSV',
    icon: FileSpreadsheet,
    active: true,
    isNew: true
  },
  // Futurs modules (désactivés pour l'instant)
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    disabled: true,
    soon: true
  },
  {
    id: 'products',
    label: 'Produits',
    icon: Package,
    disabled: true,
    soon: true
  },
  {
    id: 'settings',
    label: 'Paramètres',
    icon: Settings,
    disabled: true,
    soon: true
  },
]

function Sidebar({ activeModule, onModuleChange }) {
  return (
    <aside className="w-72 bg-luxarmonie-black text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-luxarmonie-terracotta flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-title">
              Luxarmonie
            </h1>
            <p className="text-xs text-luxarmonie-gray-400 tracking-body">
              Hub Manager
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <p className="text-xs uppercase text-luxarmonie-gray-500 font-medium mb-4 px-3 tracking-widest">
          Modules
        </p>
        
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = activeModule === item.id
            const isDisabled = item.disabled
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => !isDisabled && onModuleChange(item.id)}
                  disabled={isDisabled}
                  className={`
                    w-full flex items-center gap-3 px-3 py-3 rounded-lg
                    transition-all duration-200 group
                    ${isActive 
                      ? 'bg-luxarmonie-terracotta text-white' 
                      : isDisabled
                        ? 'text-luxarmonie-gray-600 cursor-not-allowed'
                        : 'text-luxarmonie-gray-300 hover:bg-white/5 hover:text-white'
                    }
                  `}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : ''}`} />
                  
                  <span className="flex-1 text-left font-medium tracking-body">
                    {item.label}
                  </span>
                  
                  {item.soon && (
                    <span className="text-[10px] uppercase bg-white/10 px-2 py-0.5 rounded-full">
                      Soon
                    </span>
                  )}
                  
                  {item.isNew && (
                    <span className="text-[10px] uppercase bg-green-500 text-white px-2 py-0.5 rounded-full">
                      New
                    </span>
                  )}
                  
                  {isActive && (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <div className="bg-white/5 rounded-lg p-4">
          <p className="text-xs text-luxarmonie-gray-400 mb-1">
            Version
          </p>
          <p className="text-sm font-medium">
            1.0.0
          </p>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
