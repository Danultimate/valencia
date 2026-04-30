export interface Auction {
  id: number
  title: string
  category: string | null
  location: string | null
  appraisal_value: number | null
  estimated_value: number | null
  current_bid: number | null
  start_date: string | null
  end_date: string | null
  url: string
  is_active: boolean
  opportunity_score: number | null
  last_scraped_at: string | null
  created_at: string
  time_remaining_hours: number
}

export interface AuctionListResponse {
  items: Auction[]
  total: number
  limit: number
  offset: number
}

export interface OpportunitiesResponse {
  items: Auction[]
  count: number
}

export interface HealthResponse {
  status: string
  database: string
  redis: string
  last_scraped_at: string | null
  active_auctions: number
}

export interface ScrapeTaskResponse {
  task_id: string
  status: string
  message: string
}
