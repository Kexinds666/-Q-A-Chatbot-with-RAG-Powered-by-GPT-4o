import React from 'react'
import { Bot } from 'lucide-react'

const TypingIndicator: React.FC = () => {
  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start space-x-3 max-w-3xl">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center">
          <Bot className="w-4 h-4" />
        </div>

        {/* Typing Indicator */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="typing-indicator">
            <div className="typing-dot" style={{ animationDelay: '0ms' }}></div>
            <div className="typing-dot" style={{ animationDelay: '150ms' }}></div>
            <div className="typing-dot" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator
