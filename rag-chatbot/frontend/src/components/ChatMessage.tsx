import React from 'react'
import { User, Bot, ExternalLink } from 'lucide-react'

interface Message {
  id: string
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  sources?: string[]
}

interface ChatMessageProps {
  message: Message
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatContent = (content: string) => {
    // Simple markdown-like formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>')
      .replace(/\n/g, '<br />')
  }

  return (
    <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-3xl ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          message.sender === 'user' 
            ? 'bg-primary-500 text-white' 
            : 'bg-gray-200 text-gray-600'
        }`}>
          {message.sender === 'user' ? (
            <User className="w-4 h-4" />
          ) : (
            <Bot className="w-4 h-4" />
          )}
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${message.sender === 'user' ? 'items-end' : 'items-start'}`}>
          <div className={`chat-message ${message.sender}`}>
            <div 
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ 
                __html: formatContent(message.content) 
              }}
            />
          </div>

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="text-xs text-gray-500">Sources:</p>
              {message.sources.map((source, index) => (
                <div key={index} className="flex items-center space-x-1 text-xs text-primary-600">
                  <ExternalLink className="w-3 h-3" />
                  <span className="truncate max-w-xs">{source}</span>
                </div>
              ))}
            </div>
          )}

          {/* Timestamp */}
          <span className="text-xs text-gray-400 mt-1">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default ChatMessage
