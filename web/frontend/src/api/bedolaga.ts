import { api } from './client'

export interface BedolagaOverview {
  users?: { total?: number; active?: number; blocked?: number; balance_kopeks?: number; balance_rubles?: number }
  subscriptions?: { active?: number; expired?: number }
  support?: { open_tickets?: number }
  payments?: { today_rubles?: number; today_kopeks?: number }
}

export interface BedolagaFullStats {
  users?: { total_users?: number; active_users?: number; blocked_users?: number; new_today?: number; new_week?: number; new_month?: number }
  subscriptions?: {
    active_subscriptions?: number; trial_subscriptions?: number; paid_subscriptions?: number
    trial_to_paid_conversion?: number
    trial_statistics?: { used_trials?: number; active_trials?: number; resettable_trials?: number }
  }
  transactions?: {
    totals?: { income_rubles?: number; expenses_rubles?: number; profit_rubles?: number; subscription_income_rubles?: number }
    today?: { transactions_count?: number; income_rubles?: number }
    by_type?: Record<string, { count?: number; amount?: number }>
    by_payment_method?: Record<string, { count?: number; amount?: number }>
  }
  referrals?: {
    users_with_referrals?: number; active_referrers?: number; total_paid_rubles?: number
    today_earnings_rubles?: number; week_earnings_rubles?: number; month_earnings_rubles?: number
    top_referrers?: Array<{ user_id?: number; display_name?: string; username?: string; total_earned_kopeks?: number; referrals_count?: number }>
  }
}

export interface BedolagaUser {
  id: number
  telegram_id?: number
  username?: string
  first_name?: string
  last_name?: string
  email?: string
  status?: string
  balance_kopeks?: number
  balance_rubles?: number
  created_at?: string
  last_activity?: string
  referral_code?: string
  referred_by_id?: number
  promo_group?: { id?: number; name?: string }
  tariff_id?: number
  tariff_name?: string
  subscription?: {
    id?: number
    status?: string
    end_date?: string
    is_trial?: boolean
    autopay_enabled?: boolean
    traffic_used_gb?: number
    traffic_limit_gb?: number
    device_count?: number
    device_limit?: number
    subscription_url?: string
  }
}

export const bedolagaApi = {
  // Dashboard
  getStatus: () => api.get('/bedolaga/status').then(r => r.data),
  getOverview: () => api.get('/bedolaga/overview').then(r => r.data),
  getFull: () => api.get('/bedolaga/full').then(r => r.data),
  getHealth: () => api.get('/bedolaga/health').then(r => r.data),
  getCapabilities: () => api.get('/bedolaga/capabilities').then(r => r.data),
  getMaintenance: () => api.get('/bedolaga/maintenance').then(r => r.data),

  // Tariffs (from bot DB)
  getTariffs: () => api.get('/bedolaga/tariffs').then(r => r.data),

  // Customers
  listUsers: (params: Record<string, string>) =>
    api.get(`/bedolaga/customers?${new URLSearchParams(params)}`).then(r => r.data),
  getUser: (id: number) =>
    api.get(`/bedolaga/customers/${id}`).then(r => r.data),
  updateUser: (id: number, data: Record<string, unknown>) =>
    api.patch(`/bedolaga/customers/${id}`, data).then(r => r.data),
  getUserByTelegram: (tgId: number) =>
    api.get(`/bedolaga/customers/by-telegram/${tgId}`).then(r => r.data),

  // Balance & Subscriptions
  modifyBalance: (userId: number, data: { amount_kopeks: number; reason?: string }) =>
    api.post(`/bedolaga/customers/${userId}/balance`, data).then(r => r.data),
  createSubscription: (userId: number, data: Record<string, unknown>) =>
    api.post(`/bedolaga/customers/${userId}/subscription`, data).then(r => r.data),
  deactivateSubscription: (userId: number) =>
    api.delete(`/bedolaga/customers/${userId}/subscription`).then(r => r.data),

  getSubscription: (subId: number) =>
    api.get(`/bedolaga/customers/subscriptions/${subId}`).then(r => r.data),
  extendSubscription: (subId: number, data: { days: number }) =>
    api.post(`/bedolaga/customers/subscriptions/${subId}/extend`, data).then(r => r.data),
  addTraffic: (subId: number, data: { traffic_gb: number }) =>
    api.post(`/bedolaga/customers/subscriptions/${subId}/traffic`, data).then(r => r.data),
  addDevices: (subId: number, data: { count: number }) =>
    api.post(`/bedolaga/customers/subscriptions/${subId}/devices`, data).then(r => r.data),
  resetDevices: (subId: number) =>
    api.post(`/bedolaga/customers/subscriptions/${subId}/reset-devices`).then(r => r.data),

  // Transactions
  listTransactions: (params: Record<string, string>) =>
    api.get(`/bedolaga/customers/transactions?${new URLSearchParams(params)}`).then(r => r.data),

  // Activity
  getUserActivity: (userId: number, params: Record<string, string>) =>
    api.get(`/bedolaga/customers/${userId}/activity?${new URLSearchParams(params)}`).then(r => r.data),

  // Events
  listEvents: (params: Record<string, string>) =>
    api.get(`/bedolaga/customers/events?${new URLSearchParams(params)}`).then(r => r.data),

  // Promo codes
  listPromos: (params: Record<string, string>) =>
    api.get(`/bedolaga/promo?${new URLSearchParams(params)}`).then(r => r.data),
  getPromo: (id: number) => api.get(`/bedolaga/promo/${id}`).then(r => r.data),
  getPromoStats: (id: number) => api.get(`/bedolaga/promo/${id}/stats`).then(r => r.data),
  createPromo: (data: Record<string, unknown>) =>
    api.post('/bedolaga/promo', data).then(r => r.data),
  updatePromo: (id: number, data: Record<string, unknown>) =>
    api.patch(`/bedolaga/promo/${id}`, data).then(r => r.data),
  deletePromo: (id: number) =>
    api.delete(`/bedolaga/promo/${id}`).then(r => r.data),

  // Marketing
  listCampaigns: (params: Record<string, string>) =>
    api.get(`/bedolaga/marketing/campaigns?${new URLSearchParams(params)}`).then(r => r.data),
  createCampaign: (data: Record<string, unknown>) =>
    api.post('/bedolaga/marketing/campaigns', data).then(r => r.data),
  updateCampaign: (id: number, data: Record<string, unknown>) =>
    api.patch(`/bedolaga/marketing/campaigns/${id}`, data).then(r => r.data),
  deleteCampaign: (id: number) =>
    api.delete(`/bedolaga/marketing/campaigns/${id}`).then(r => r.data),
  listBroadcasts: (params: Record<string, string>) =>
    api.get(`/bedolaga/marketing/broadcasts?${new URLSearchParams(params)}`).then(r => r.data),
  createBroadcast: (data: Record<string, unknown>) =>
    api.post('/bedolaga/marketing/broadcasts', data).then(r => r.data),
  stopBroadcast: (id: number) =>
    api.post(`/bedolaga/marketing/broadcasts/${id}/stop`).then(r => r.data),
  listPartners: (params: Record<string, string>) =>
    api.get(`/bedolaga/marketing/partners?${new URLSearchParams(params)}`).then(r => r.data),

  // Referrals
  getReferralStats: () => api.get('/bedolaga/referrals/stats').then(r => r.data),
  listReferrers: (params: Record<string, string>) =>
    api.get(`/bedolaga/referrals/referrers?${new URLSearchParams(params)}`).then(r => r.data),
  getReferrerRefs: (id: number) =>
    api.get(`/bedolaga/referrals/referrers/${id}/refs`).then(r => r.data),
}