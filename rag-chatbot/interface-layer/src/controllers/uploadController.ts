import { Request, Response } from 'express'
import axios from 'axios'
import { logger } from '../utils/logger'
import { redisClient } from '../services/redis'

export const uploadController = {
  uploadFile: async (req: Request, res: Response): Promise<void> => {
    try {
      if (!req.file) {
        res.status(400).json({ error: 'No file uploaded' })
        return
      }

      const file = req.file
      logger.info(`File upload started: ${file.originalname} (${file.size} bytes)`)

      // Forward file to AI backend service
      const formData = new FormData()
      formData.append('file', new Blob([file.buffer]), file.originalname)

      const response = await axios.post(
        `${process.env.AI_BACKEND_URL}/api/documents/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 60000, // 60 second timeout for file processing
        }
      )

      // Cache the upload result
      const uploadId = response.data.upload_id
      await redisClient.setex(`upload:${uploadId}`, 3600, JSON.stringify({
        filename: file.originalname,
        size: file.size,
        status: 'completed',
        timestamp: new Date().toISOString()
      }))

      logger.info(`File upload completed: ${file.originalname}`)
      res.json({
        message: 'File uploaded and processed successfully',
        upload_id: uploadId,
        filename: file.originalname,
        chunks_created: response.data.chunks_created
      })

    } catch (error: any) {
      logger.error('File upload error:', error)
      
      if (error.response) {
        res.status(error.response.status).json({
          error: error.response.data.error || 'File processing failed'
        })
      } else if (error.code === 'ECONNREFUSED') {
        res.status(503).json({
          error: 'AI backend service unavailable'
        })
      } else {
        res.status(500).json({
          error: 'Internal server error during file upload'
        })
      }
    }
  }
}
