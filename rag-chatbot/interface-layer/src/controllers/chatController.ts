import { Request, Response } from 'express'
import axios from 'axios'
import { logger } from '../utils/logger'
import { redisClient } from '../services/redis'

export const chatController = {
  sendMessage: async (req: Request, res: Response): Promise<void> => {
    try {
      const { message, session_id } = req.body

      if (!message || typeof message !== 'string') {
        res.status(400).json({ error: 'Message is required' })
        return
      }

      logger.info(`Chat message received: ${message.substring(0, 100)}...`)

      // Forward message to AI backend service
      const response = await axios.post(
        `${process.env.AI_BACKEND_URL}/api/chat`,
        {
          message,
          session_id: session_id || 'default'
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000, // 30 second timeout
        }
      )

      // Cache the response
      const cacheKey = `chat:${session_id || 'default'}:${Date.now()}`
      await redisClient.setex(cacheKey, 3600, JSON.stringify({
        message,
        response: response.data,
        timestamp: new Date().toISOString()
      }))

      res.json(response.data)

    } catch (error: any) {
      logger.error('Chat error:', error)
      
      if (error.response) {
        res.status(error.response.status).json({
          error: error.response.data.error || 'Chat processing failed'
        })
      } else if (error.code === 'ECONNREFUSED') {
        res.status(503).json({
          error: 'AI backend service unavailable'
        })
      } else {
        res.status(500).json({
          error: 'Internal server error during chat processing'
        })
      }
    }
  },

  getChatHistory: async (req: Request, res: Response): Promise<void> => {
    try {
      const { session_id } = req.query
      const sessionKey = session_id || 'default'

      // Get chat history from Redis
      const keys = await redisClient.keys(`chat:${sessionKey}:*`)
      const history = []

      for (const key of keys) {
        const data = await redisClient.get(key)
        if (data) {
          history.push(JSON.parse(data))
        }
      }

      // Sort by timestamp
      history.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

      res.json({ history })

    } catch (error: any) {
      logger.error('Get chat history error:', error)
      res.status(500).json({ error: 'Failed to retrieve chat history' })
    }
  },

  getDocuments: async (req: Request, res: Response): Promise<void> => {
    try {
      const response = await axios.get(`${process.env.AI_BACKEND_URL}/api/documents`)
      res.json(response.data)
    } catch (error: any) {
      logger.error('Get documents error:', error)
      res.status(500).json({ error: 'Failed to retrieve documents' })
    }
  },

  deleteDocument: async (req: Request, res: Response): Promise<void> => {
    try {
      const { id } = req.params
      const response = await axios.delete(`${process.env.AI_BACKEND_URL}/api/documents/${id}`)
      res.json(response.data)
    } catch (error: any) {
      logger.error('Delete document error:', error)
      res.status(500).json({ error: 'Failed to delete document' })
    }
  }
}
