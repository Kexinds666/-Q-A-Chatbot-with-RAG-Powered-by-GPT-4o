import { Server, Socket } from 'socket.io'
import axios from 'axios'
import { logger } from '../utils/logger'
import { redisClient } from '../services/redis'

interface ChatMessage {
  content: string
  session_id?: string
}

export const setupSocketHandlers = (io: Server): void => {
  io.on('connection', (socket: Socket) => {
    logger.info(`Client connected: ${socket.id}`)

    // Handle chat messages
    socket.on('message', async (data: ChatMessage, callback) => {
      try {
        const { content, session_id } = data

        if (!content || typeof content !== 'string') {
          callback({ error: 'Message content is required' })
          return
        }

        logger.info(`Socket message received from ${socket.id}: ${content.substring(0, 100)}...`)

        // Forward to AI backend service
        const response = await axios.post(
          `${process.env.AI_BACKEND_URL}/api/chat/stream`,
          {
            message: content,
            session_id: session_id || socket.id
          },
          {
            headers: {
              'Content-Type': 'application/json',
            },
            timeout: 30000,
          }
        )

        // Cache the interaction
        const cacheKey = `socket:${socket.id}:${Date.now()}`
        await redisClient.setex(cacheKey, 3600, JSON.stringify({
          message: content,
          response: response.data,
          timestamp: new Date().toISOString()
        }))

        // Send response back to client
        socket.emit('message', {
          id: Date.now().toString(),
          content: response.data.answer,
          sources: response.data.sources,
          timestamp: new Date().toISOString()
        })

        // Acknowledge the message
        callback({ success: true })

      } catch (error: any) {
        logger.error('Socket message error:', error)
        
        const errorMessage = error.response?.data?.error || 'Failed to process message'
        socket.emit('error', { message: errorMessage })
        callback({ error: errorMessage })
      }
    })

    // Handle typing indicators
    socket.on('typing', (data) => {
      socket.broadcast.emit('user-typing', {
        user_id: socket.id,
        is_typing: data.is_typing
      })
    })

    // Handle disconnection
    socket.on('disconnect', (reason) => {
      logger.info(`Client disconnected: ${socket.id}, reason: ${reason}`)
    })

    // Handle errors
    socket.on('error', (error) => {
      logger.error(`Socket error from ${socket.id}:`, error)
    })
  })

  // Broadcast system messages
  setInterval(() => {
    io.emit('system', {
      type: 'heartbeat',
      timestamp: new Date().toISOString(),
      connected_clients: io.engine.clientsCount
    })
  }, 30000) // Every 30 seconds
}
