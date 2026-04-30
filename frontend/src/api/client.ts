import type { AuctionListResponse, HealthResponse, OpportunitiesResponse, ScrapeTaskResponse } from '../types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export function fetchAuctions(params: {
  category?: string
  active_only?: boolean
  limit?: number
  offset?: number
}): Promise<AuctionListResponse> {
  const q = new URLSearchParams()
  if (params.category) q.set('category', params.category)
  if (params.active_only !== undefined) q.set('active_only', String(params.active_only))
  if (params.limit !== undefined) q.set('limit', String(params.limit))
  if (params.offset !== undefined) q.set('offset', String(params.offset))
  return request<AuctionListResponse>(`/items?${q}`)
}

export function fetchOpportunities(params: {
  min_score?: number
  limit?: number
}): Promise<OpportunitiesResponse> {
  const q = new URLSearchParams()
  if (params.min_score !== undefined) q.set('min_score', String(params.min_score))
  if (params.limit !== undefined) q.set('limit', String(params.limit))
  return request<OpportunitiesResponse>(`/opportunities?${q}`)
}

export function triggerScrape(apiKey: string): Promise<ScrapeTaskResponse> {
  return request<ScrapeTaskResponse>('/scrape/trigger', {
    method: 'POST',
    headers: { 'X-API-Key': apiKey },
  })
}
