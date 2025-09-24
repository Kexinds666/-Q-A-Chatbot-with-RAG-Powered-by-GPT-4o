import { useState } from 'react'
import { Socket } from 'socket.io-client'

export const useChat = (socket: Socket | null) => {
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = async (message: string): Promise<void> => {
    if (!socket) {
      throw new Error('Socket not connected')
    }

    setIsLoading(true)
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        setIsLoading(false)
        reject(new Error('Request timeout'))
      }, 30000) // 30 second timeout

      socket.emit('message', { content: message }, (response: any) => {
        clearTimeout(timeout)
        setIsLoading(false)
        
        if (response.error) {
          reject(new Error(response.error))
        } else {
          resolve()
        }
      })
    })
  }

  return { sendMessage, isLoading }
}
