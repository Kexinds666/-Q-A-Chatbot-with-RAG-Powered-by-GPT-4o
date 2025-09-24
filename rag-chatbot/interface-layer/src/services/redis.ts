import { createClient } from 'redis'
import { logger } from '../utils/logger'

const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379'

export const redisClient = createClient({
  url: redisUrl,
  socket: {
    reconnectStrategy: (retries) => {
      if (retries > 10) {
        logger.error('Redis connection failed after 10 retries')
        return new Error('Redis connection failed')
      }
      return Math.min(retries * 100, 3000)
    }
  }
})

redisClient.on('error', (err) => {
  logger.error('Redis Client Error:', err)
})

redisClient.on('connect', () => {
  logger.info('Redis client connected')
})

redisClient.on('ready', () => {
  logger.info('Redis client ready')
})

redisClient.on('end', () => {
  logger.info('Redis client disconnected')
})

// Connect to Redis
redisClient.connect().catch((err) => {
  logger.error('Failed to connect to Redis:', err)
})

export default redisClient
