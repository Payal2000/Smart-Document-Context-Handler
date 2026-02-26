import { motion } from 'framer-motion'
import { useState } from 'react'
import { queryDocument } from '../api/client'
import type { QueryResponse, UploadResponse } from '../types'
import { ChunkViewer } from './ChunkViewer'
import { TierBadge } from './TierBadge'
import { TokenBudgetChart } from './TokenBudgetChart'

interface Props {
  document: UploadResponse
}

export function QueryInterface({ document: doc }: Props) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleQuery = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await queryDocument(doc.doc_id, query)
      setResult(res)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Document summary */}
      <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="font-semibold text-gray-800 text-lg">{doc.filename}</h2>
            <p className="text-sm text-gray-400 mt-0.5">
              {(doc.file_size / 1024).toFixed(1)} KB
              {doc.page_count && ` · ${doc.page_count} pages`}
              {doc.row_count && ` · ${doc.row_count} rows`}
            </p>
          </div>
          <TierBadge tier={doc.tier} tokenCount={doc.token_count} />
        </div>
      </div>

      {/* Token budget chart */}
      <TokenBudgetChart budget={doc.budget} />

      {/* Query box */}
      <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Ask a question about this document
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
            placeholder="e.g. What are the main findings?"
            className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={handleQuery}
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium
              disabled:opacity-50 disabled:cursor-not-allowed hover:bg-indigo-700 transition-colors"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Searching…
              </span>
            ) : (
              'Search'
            )}
          </motion.button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <TokenBudgetChart budget={result.budget} />
          <ChunkViewer
            chunks={result.chunks_used}
            assembledContext={result.assembled_context}
            strategyNotes={result.strategy_notes}
          />
        </motion.div>
      )}
    </div>
  )
}
