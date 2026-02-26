import { motion } from 'framer-motion'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadDocument } from '../api/client'
import type { UploadResponse } from '../types'

const ACCEPTED_TYPES = {
  'text/plain': ['.txt', '.md'],
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/csv': ['.csv'],
  'text/tab-separated-values': ['.tsv'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
}

interface Props {
  onUploaded: (result: UploadResponse) => void
}

export function FileUpload({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0]
      if (!file) return

      setUploading(true)
      setError(null)
      try {
        const result = await uploadDocument(file)
        onUploaded(result)
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Upload failed. Please try again.'
        setError(msg)
      } finally {
        setUploading(false)
      }
    },
    [onUploaded],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  })

  return (
    <div className="w-full">
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: uploading ? 1 : 1.01 }}
        whileTap={{ scale: uploading ? 1 : 0.99 }}
        className={`
          relative flex flex-col items-center justify-center gap-4 p-12 rounded-2xl border-2 border-dashed
          cursor-pointer transition-colors select-none
          ${isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-indigo-50/40'}
          ${uploading ? 'opacity-70 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <>
            <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-indigo-600 font-medium">Analyzing document…</p>
          </>
        ) : (
          <>
            <div className="w-14 h-14 bg-indigo-100 rounded-2xl flex items-center justify-center text-indigo-500 text-2xl">
              📄
            </div>
            <div className="text-center">
              <p className="font-semibold text-gray-700 text-lg">
                {isDragActive ? 'Drop it here!' : 'Drop a document or click to browse'}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                .txt · .md · .pdf · .docx · .csv · .tsv · .xlsx — max 50 MB
              </p>
            </div>
          </>
        )}
      </motion.div>

      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 text-sm text-red-600 font-medium"
        >
          {error}
        </motion.p>
      )}
    </div>
  )
}
