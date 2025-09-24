import { Express } from 'express'
import multer from 'multer'
import { uploadController } from '../controllers/uploadController'
import { chatController } from '../controllers/chatController'
import { validateUpload } from '../middleware/validation'

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true)
    } else {
      cb(new Error('Invalid file type. Only PDF, TXT, and DOCX files are allowed.'))
    }
  }
})

export const setupRoutes = (app: Express): void => {
  // File upload endpoint
  app.post('/api/upload', upload.single('file'), validateUpload, uploadController.uploadFile)
  
  // Chat endpoints
  app.post('/api/chat', chatController.sendMessage)
  app.get('/api/chat/history', chatController.getChatHistory)
  
  // Document management
  app.get('/api/documents', chatController.getDocuments)
  app.delete('/api/documents/:id', chatController.deleteDocument)
}
