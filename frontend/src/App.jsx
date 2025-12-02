import { useState } from 'react'
import Sidebar from './components/Sidebar'
import PricingModule from './components/PricingModule'

function App() {
  const [activeModule, setActiveModule] = useState('pricing')

  return (
    <div className="flex h-screen bg-luxarmonie-gray-50">
      {/* Sidebar */}
      <Sidebar 
        activeModule={activeModule} 
        onModuleChange={setActiveModule} 
      />
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {activeModule === 'pricing' && <PricingModule />}
          
          {/* Placeholder pour futurs modules */}
          {activeModule !== 'pricing' && (
            <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
              <div className="text-center">
                <p className="text-luxarmonie-gray-400 text-lg">
                  Module en cours de développement
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
