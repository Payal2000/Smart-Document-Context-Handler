import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { FileUpload } from './components/FileUpload'
import { QueryInterface } from './components/QueryInterface'
import type { UploadResponse } from './types'

export default function App() {
  const [uploaded, setUploaded] = useState<UploadResponse | null>(null)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-indigo-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
              S
            </div>
            <div>
              <h1 className="font-bold text-gray-900 leading-tight">
                Smart Document Context Handler
              </h1>
              <p className="text-xs text-gray-400">Intelligent 4-tier LLM context optimization</p>
            </div>
          </div>

          {uploaded && (
            <button
              onClick={() => setUploaded(null)}
              className="text-sm text-indigo-600 hover:underline font-medium"
            >
              ← Upload another
            </button>
          )}
        </div>
      </header>

      {/* Tier legend */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 py-2 flex gap-6 text-xs text-gray-500 overflow-x-auto">
          {[
            { tier: 1, label: 'Direct Injection', color: '#22c55e', range: '≤12K tokens' },
            { tier: 2, label: 'Smart Trimming', color: '#3b82f6', range: '12–25K tokens' },
            { tier: 3, label: 'Strategic Chunking', color: '#f59e0b', range: '25–50K tokens' },
            { tier: 4, label: 'RAG Retrieval', color: '#ef4444', range: '>50K tokens' },
          ].map((t) => (
            <div key={t.tier} className="flex items-center gap-1.5 shrink-0">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: t.color }} />
              <span>
                <strong>T{t.tier}</strong> {t.label}
              </span>
              <span className="opacity-50">({t.range})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-6 py-10">
        <AnimatePresence mode="wait">
          {!uploaded ? (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
            >
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-800">Upload a Document</h2>
                <p className="text-gray-500 mt-2">
                  The system will automatically classify it into the optimal processing tier.
                </p>
              </div>
              <FileUpload onUploaded={setUploaded} />
            </motion.div>
          ) : (
            <motion.div
              key="query"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
            >
              <QueryInterface document={uploaded} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
