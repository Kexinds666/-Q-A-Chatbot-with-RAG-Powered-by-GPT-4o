import { useState } from 'react'

export const useFileUpload = () => {
  const [isUploading, setIsUploading] = useState(false)

  const uploadFile = async (file: File): Promise<void> => {
    setIsUploading(true)
    
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Upload failed')
      }

      const result = await response.json()
      console.log('File uploaded successfully:', result)
    } catch (error) {
      console.error('Upload error:', error)
      throw error
    } finally {
      setIsUploading(false)
    }
  }

  return { uploadFile, isUploading }
}
