import GenieChat from './components/GenieChat'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-databricks-dark mb-2">
            Databricks Genie Integration
          </h1>
          <p className="text-gray-600">
            AI-powered conversational interface for data insights
          </p>
        </div>
        <GenieChat />
      </div>
    </div>
  )
}

export default App