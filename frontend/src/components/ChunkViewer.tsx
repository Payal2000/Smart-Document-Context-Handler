import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import type { ChunkInfo } from '../types'

interface Props {
  chunks: ChunkInfo[]
  assembledContext: string
  strategyNotes: string
}

export function ChunkViewer({ chunks, assembledContext, strategyNotes }: Props) {
  const [tab, setTab] = useState<'chunks' | 'context'>('chunks')
  const [expanded, setExpanded] = useState(false)

  const contextPreview = expanded ? assembledContext : assembledContext.slice(0, 800)
  const canExpand = assembledContext.length > 800

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-gray-200">
        {(['chunks', 'context'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-3 text-sm font-medium transition-colors ${
              tab === t
                ? 'border-b-2 border-indigo-500 text-indigo-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'chunks' ? `Chunks Used (${chunks.length})` : 'Assembled Context'}
          </button>
        ))}
      </div>

      <div className="p-5">
        {/* Strategy notes */}
        {strategyNotes && (
          <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 mb-4">
            {strategyNotes}
          </p>
        )}

        <AnimatePresence mode="wait">
          {tab === 'chunks' ? (
            <motion.div
              key="chunks"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2"
            >
              {chunks.length === 0 ? (
                <p className="text-sm text-gray-400">No chunks (full document used directly)</p>
              ) : (
                chunks.map((c, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between px-4 py-2 bg-gray-50 rounded-lg text-sm"
                  >
                    <span className="text-gray-600 font-mono">Chunk #{c.index}</span>
                    <span className="text-gray-400">{c.tokens.toLocaleString()} tokens</span>
                    {c.score < 1 && (
                      <span className="text-indigo-500 font-medium">
                        score: {c.score.toFixed(3)}
                      </span>
                    )}
                  </div>
                ))
              )}
            </motion.div>
          ) : (
            <motion.div
              key="context"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <pre className="text-xs text-gray-700 bg-gray-50 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                {contextPreview}
                {!expanded && canExpand && '…'}
              </pre>
              {canExpand && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="mt-2 text-xs text-indigo-600 hover:underline"
                >
                  {expanded ? 'Show less' : 'Show full context'}
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
