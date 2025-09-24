import React, { useState, useEffect, useRef } from 'react'
import { Send, Upload, Bot, User, Loader2 } from 'lucide-react'
import { useSocket } from './hooks/useSocket'
import { useChat } from './hooks/useChat'
import { useFileUpload } from './hooks/useFileUpload'
import ChatMessage from './components/ChatMessage'
import FileUploadModal from './components/FileUploadModal'
import TypingIndicator from './components/TypingIndicator'

interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  sources?: string[]
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const { socket } = useSocket()
  const { sendMessage, isLoading } = useChat(socket)
  const { uploadFile, isUploading } = useFileUpload()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (socket) {
      socket.on('connect', () => {
        setIsConnected(true)
        console.log('Connected to server')
      })

      socket.on('disconnect', () => {
        setIsConnected(false)
        console.log('Disconnected from server')
      })

      socket.on('message', (data: any) => {
        const newMessage: Message = {
          id: data.id || Date.now().toString(),
          content: data.content,
          sender: 'assistant',
          timestamp: new Date(),
          sources: data.sources
        }
        setMessages(prev => [...prev, newMessage])
      })

      socket.on('error', (error: any) => {
        console.error('Socket error:', error)
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `Error: ${error.message || 'Something went wrong'}`,
          sender: 'assistant',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
      })

      return () => {
        socket.off('connect')
        socket.off('disconnect')
        socket.off('message')
        socket.off('error')
      }
    }
  }, [socket])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')

    try {
      await sendMessage(inputValue)
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  const handleFileUpload = async (file: File) => {
    try {
      await uploadFile(file)
      setIsUploadModalOpen(false)
    } catch (error) {
      console.error('Failed to upload file:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">RAG Chatbot</h1>
              <p className="text-sm text-gray-500">
                {isConnected ? 'Connected' : 'Connecting...'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="btn-secondary flex items-center space-x-2"
            disabled={isUploading}
          >
            <Upload className="w-4 h-4" />
            <span>Upload Document</span>
          </button>
        </div>
      </header>

      {/* Chat Messages */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h2 className="text-xl font-medium text-gray-900 mb-2">
                Welcome to RAG Chatbot
              </h2>
              <p className="text-gray-500 mb-6">
                Ask me anything about your uploaded documents, or upload a new document to get started.
              </p>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="btn-primary"
              >
                Upload Your First Document
              </button>
            </div>
          )}

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Form */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="input-field flex-1"
              disabled={isLoading || !isConnected}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading || !isConnected}
              className="btn-primary flex items-center space-x-2"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Send</span>
            </button>
          </form>
        </div>
      </footer>

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUpload={handleFileUpload}
        isUploading={isUploading}
      />
    </div>
  )
}

export default App
