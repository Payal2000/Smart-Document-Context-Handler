import axios from 'axios'
import type { QueryResponse, UploadResponse } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<UploadResponse>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function queryDocument(
  docId: string,
  query: string,
  topK = 10,
): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>('/query/', { doc_id: docId, query, top_k: topK })
  return data
}
