import React, { useState, useEffect, useRef } from 'react'
import {
  Send,
  User,
  Bot,
  Loader2,
  AlertCircle,
  Code,
  ChevronDown,
  ChevronRight,
  Table,
  Sparkles
} from 'lucide-react'

interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
  sql?: string
  results?: any
}

const GenieChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm your Databricks Genie assistant. I can help you analyze data, write SQL queries, and provide insights. How can I help you today?",
      sender: 'assistant',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSqlFor, setShowSqlFor] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const toggleSqlVisibility = (messageId: string) => {
    setShowSqlFor(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      sender: 'user',
      timestamp: new Date(),
      status: 'sending'
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/genie/send-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: userMessage.content,
          conversation_id: conversationId
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const data = await response.json()

      // Update conversation ID if new
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id)
      }

      // Add assistant response
      const assistantMessage: Message = {
        id: data.message_id || Date.now().toString(),
        content: data.content,
        sender: 'assistant',
        timestamp: new Date(data.timestamp),
        sql: data.sql_query,
        results: data.query_results
      }

      setMessages(prev => [
        ...prev.slice(0, -1),
        { ...userMessage, status: 'sent' },
        assistantMessage
      ])
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
      setMessages(prev => [
        ...prev.slice(0, -1),
        { ...userMessage, status: 'error' }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const suggestedQuestions = [
    "What tables are available?",
    "Show me the schema of a table",
    "Analyze data trends",
    "Help me write a SQL query"
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-databricks-red to-databricks-orange p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-databricks-red" />
              </div>
              <div className="text-white">
                <h2 className="font-semibold">Genie Assistant</h2>
                <p className="text-sm opacity-90">
                  {conversationId ? 'Connected' : 'New Conversation'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="h-[500px] overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2 max-w-[80%]`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.sender === 'user'
                    ? 'bg-blue-100 ml-2'
                    : 'bg-databricks-red/10 mr-2'
                }`}>
                  {message.sender === 'user' ? (
                    <User className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Bot className="w-5 h-5 text-databricks-red" />
                  )}
                </div>
                <div className="space-y-2">
                  <div className={`rounded-lg px-4 py-2 ${
                    message.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-900 border border-gray-200'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    {message.status === 'sending' && (
                      <Loader2 className="w-3 h-3 animate-spin mt-1" />
                    )}
                    {message.status === 'error' && (
                      <AlertCircle className="w-3 h-3 text-red-400 mt-1" />
                    )}
                  </div>

                  {/* SQL Query */}
                  {message.sql && (
                    <div className="mt-2">
                      <button
                        onClick={() => toggleSqlVisibility(message.id)}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                      >
                        {showSqlFor.has(message.id) ? (
                          <ChevronDown className="w-3 h-3" />
                        ) : (
                          <ChevronRight className="w-3 h-3" />
                        )}
                        <Code className="w-3 h-3" />
                        <span>View SQL Query</span>
                      </button>

                      {showSqlFor.has(message.id) && (
                        <div className="mt-2 bg-gray-900 text-gray-100 rounded-lg p-3">
                          <pre className="text-xs overflow-x-auto">
                            <code>{message.sql}</code>
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Query Results */}
                  {message.results && (
                    <div className="mt-2 bg-white border border-gray-200 rounded-lg overflow-hidden">
                      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-b">
                        <Table className="w-4 h-4 text-databricks-red" />
                        <span className="text-xs font-medium text-gray-700">Query Results</span>
                        {message.results.row_count !== undefined && (
                          <span className="text-xs text-gray-500 ml-auto">
                            {message.results.row_count} row{message.results.row_count !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>

                      {message.results.columns && message.results.data ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full">
                            <thead className="bg-gray-50">
                              <tr className="border-b">
                                {message.results.columns.map((col: string, idx: number) => (
                                  <th key={idx} className="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {message.results.data.slice(0, 10).map((row: any[], rowIdx: number) => (
                                <tr key={rowIdx} className="hover:bg-gray-50">
                                  {row.map((value: any, colIdx: number) => (
                                    <td key={colIdx} className="px-3 py-2 text-sm text-gray-900">
                                      {value !== null && value !== undefined ? (
                                        String(value)
                                      ) : (
                                        <span className="text-gray-400 italic">null</span>
                                      )}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {message.results.data.length > 10 && (
                            <div className="px-3 py-2 bg-gray-50 border-t text-xs text-gray-500 text-center">
                              Showing first 10 rows of {message.results.row_count} total
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="p-3 text-xs text-gray-600">
                          <pre>{JSON.stringify(message.results, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}

                  <span className="text-xs text-gray-400">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center space-x-2 bg-white border border-gray-200 rounded-lg px-4 py-2">
                <Loader2 className="w-4 h-4 animate-spin text-databricks-red" />
                <span className="text-sm text-gray-600">Genie is thinking...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-600" />
                <span className="text-sm text-red-800">{error}</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions */}
        {messages.length === 1 && (
          <div className="px-4 pb-2 bg-gray-50">
            <p className="text-xs text-gray-500 mb-2">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(question)}
                  className="text-xs px-3 py-1 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask Genie about your data..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-databricks-red focus:border-transparent"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="px-4 py-2 bg-databricks-red text-white rounded-lg hover:bg-databricks-red/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Press Enter to send • Powered by Databricks Genie
          </p>
        </div>
      </div>
    </div>
  )
}

export default GenieChat