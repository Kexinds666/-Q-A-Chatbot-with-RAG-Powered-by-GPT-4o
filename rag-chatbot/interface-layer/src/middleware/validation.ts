import { Request, Response, NextFunction } from 'express'
import { body, validationResult } from 'express-validator'

export const validateUpload = [
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      })
    }
    next()
  }
]

export const validateChatMessage = [
  body('message')
    .isString()
    .isLength({ min: 1, max: 1000 })
    .withMessage('Message must be between 1 and 1000 characters'),
  body('session_id')
    .optional()
    .isString()
    .isLength({ min: 1, max: 100 })
    .withMessage('Session ID must be between 1 and 100 characters'),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req)
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation failed',
        details: errors.array()
      })
    }
    next()
  }
]
