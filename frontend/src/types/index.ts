export interface TierInfo {
  tier: 1 | 2 | 3 | 4
  label: string
  color: string
  description: string
}

export interface TokenBudgetAllocations {
  system_prompt: number
  conversation_history: number
  response_buffer: number
  document_content: number
}

export interface TokenBudgetDocument {
  original_tokens: number
  allocated_tokens: number
  max_tokens: number
  utilization_pct: number
  truncated: boolean
}

export interface TokenBudget {
  total_window: number
  allocations: TokenBudgetAllocations
  document: TokenBudgetDocument
}

export interface UploadResponse {
  doc_id: string
  filename: string
  file_size: number
  token_count: number
  tier: TierInfo
  budget: TokenBudget
  mime_type?: string
  page_count?: number
  row_count?: number
  created_at: string
}

export interface ChunkInfo {
  index: number
  tokens: number
  score: number
}

export interface QueryResponse {
  doc_id: string
  query: string
  tier: number
  assembled_context: string
  token_count: number
  chunks_used: ChunkInfo[]
  strategy_notes: string
  budget: TokenBudget
}
