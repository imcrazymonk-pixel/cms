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

export interface BedolagaSubscription {
  id?: number
  status?: string
  actual_status?: string
  start_date?: string
  end_date?: string
  is_trial?: boolean
  tariff_id?: number | null
  tariff_name?: string | null
  autopay_enabled?: boolean
  autopay_days_before?: number | null
  autopay_period_days?: number | null
  traffic_used_gb?: number
  traffic_limit_gb?: number
  device_count?: number
  device_limit?: number
  subscription_url?: string
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
  // Нормализовано бэкендом (§1.21): верхний уровень даже если данные лежали в subscription/subscriptions[]
  tariff_id?: number | null
  tariff_name?: string | null
  tariff_missing?: boolean
  subscription?: BedolagaSubscription
}

// ── Analytics (/api/bedolaga/analytics/*) ──

export interface BedolagaTariffPeriodPrice {
  days: number
  price_kopeks: number
  price_rubles: number
  samples?: number | null
  last_seen_at?: string | null
}

export interface BedolagaAnalyticsTariff {
  tariff_id: number | null
  tariff_name: string
  normalized_name: string
  is_active: boolean
  is_free: boolean
  price_known: boolean
  price_source: string
  price_kind: string
  confidence: string
  period_prices?: BedolagaTariffPeriodPrice[]
  monthly_price_kopeks: number | null
  monthly_price_rubles: number | null
  price_per_day_kopeks: number | null
  price_basis: string
  clients_paid: number
  clients_trial: number
  clients_total: number
  share_pct: number
  mrr_kopeks: number
  paid_forward_kopeks: number
  next_month_expected_kopeks: number
  unknown_price_clients: number
}

export interface BedolagaAnalyticsWarning {
  code: string
  message: string
  [key: string]: unknown
}

export interface BedolagaAnalyticsCoverage {
  users_total: number
  clients_with_paid: number
  active_paid_subscriptions: number
  trial_subscriptions: number
  clients_without_subscription: number
  price_known_subscriptions: number
  price_unknown_subscriptions: number
  price_coverage_pct: number
}

export interface BedolagaAnalyticsTariffs {
  currency: string
  price_source_priority: string[]
  coverage: BedolagaAnalyticsCoverage
  items: BedolagaAnalyticsTariff[]
  totals: {
    clients_paid: number
    clients_trial: number
    clients_without_subscription: number
    mrr_kopeks: number
    mrr_basis: string
    mrr_is_lower_bound: boolean
    mrr_unknown_subscriptions: number
    paid_forward_kopeks: number
    next_month_expected_kopeks: number
    unknown_price_clients: number
  }
  generated_at: string
  as_of: string
  partial: boolean
  warnings: BedolagaAnalyticsWarning[]
  sources: Record<string, unknown>
}

export interface BedolagaAnalyticsCustomerUser {
  id: number | null
  username?: string | null
  telegram_id?: number | null
  first_name?: string | null
}

export interface BedolagaAnalyticsPrimarySubscription {
  id: number | null
  status?: string | null
  actual_status?: string | null
  is_trial: boolean
  tariff_id: number | null
  tariff_name: string
  start_date: string | null
  end_date: string | null
  days_left: number
  autopay_enabled: boolean
  autopay_days_before: number | null
  autopay_period_days: number | null
  period_days: number
}

export interface BedolagaAnalyticsCustomerTariff {
  price_known: boolean
  price_source: string
  price_kind: string
  price_basis: string
  confidence: string
  is_free: boolean
  monthly_price_kopeks: number | null
  monthly_price_rubles: number | null
  monthly_basis: string
  monthly_source: string
  period_price_kopeks: number | null
  period_price_rubles: number | null
  period_basis: string
  period_days: number
  price_per_day_kopeks: number | null
  samples: number
  last_seen_at: string | null
}

export interface BedolagaAnalyticsCustomerMoney {
  paid_total_kopeks: number
  paid_last_12m_kopeks: number
  paid_current_month_kopeks: number
  paid_forward_kopeks: number | null
  next_payment_date: string | null
  expected_charge_date: string | null
  next_payment_kopeks: number | null
  next_payment_known: boolean
}

export interface BedolagaAnalyticsCustomerSubscription {
  id: number | null
  tariff_id: number | null
  tariff_name: string
  end_date: string | null
  is_trial: boolean
  status?: string | null
  actual_status?: string | null
}

export interface BedolagaAnalyticsCustomerPayment {
  id: number | null
  created_at: string | null
  amount_kopeks: number | null
  description?: string | null
  type?: string | null
}

export interface BedolagaAnalyticsCustomer {
  user: BedolagaAnalyticsCustomerUser
  primary_subscription: BedolagaAnalyticsPrimarySubscription | null
  tariff: BedolagaAnalyticsCustomerTariff | null
  money: BedolagaAnalyticsCustomerMoney
  subscriptions: BedolagaAnalyticsCustomerSubscription[]
  payments: BedolagaAnalyticsCustomerPayment[]
  generated_at: string
  as_of: string
  partial: boolean
  warnings: BedolagaAnalyticsWarning[]
  sources: Record<string, unknown>
}

export interface BedolagaAnalyticsSources {
  bot_db?: { status?: string; checked_at?: string | null; tariffs?: number }
  transactions?: { status?: string; scanned?: number; named_price_samples?: number; total?: number }
  users?: { status?: string; loaded?: number; total?: number }
  full_stats?: { status?: string }
}

export interface BedolagaAnalyticsOverviewTariff {
  tariff_id: number | null
  tariff_name: string
  clients_paid: number
  clients_trial: number
  share_pct: number
  monthly_price_kopeks: number | null
  price_source: string
  price_kind: string
  mrr_kopeks: number
  paid_forward_kopeks: number
  next_month_expected_kopeks: number
  unknown_price_clients: number
  is_free: boolean
}

export interface BedolagaAnalyticsOverviewKpis {
  mrr_kopeks: number
  mrr_rubles: number
  mrr_basis: string
  mrr_is_lower_bound: boolean
  mrr_unknown_subscriptions: number
  cash_forecast_next_month_kopeks: number
  cash_forecast_unknown_count: number
  renewals_due_next_month_kopeks: number
  renewals_due_next_month_count: number
  paid_forward_kopeks: number
  accrual_revenue_current_month_kopeks: number | null
  accrual_unknown_subscriptions: number
  accrual_revenue_month_kopeks: number | null
  accrual_month_unknown_subscriptions: number
  cash_received_current_month_kopeks: number
  cash_received_month_kopeks: number
  payments_current_month: number
  active_paid_clients: number
  active_paid_subscriptions: number
  autopay_enabled_subscriptions: number
}

export interface BedolagaAnalyticsMonthlyPoint {
  month: string
  cash_received_kopeks: number
  cash_received_rubles: number
  payments_count: number
  unique_payers: number
  renewal_payments: number
  purchase_payments: number
  renewal_proxy: number | null
  avg_payment_kopeks: number | null
  accrual_revenue_kopeks: number | null
  accrual_is_estimate: boolean
}

export interface BedolagaAnalyticsOverview {
  month: string
  next_month: string
  basis: string
  coverage: BedolagaAnalyticsCoverage
  kpis: BedolagaAnalyticsOverviewKpis
  by_tariff: BedolagaAnalyticsOverviewTariff[]
  monthly: BedolagaAnalyticsMonthlyPoint[]
  generated_at: string
  as_of: string
  partial: boolean
  warnings: BedolagaAnalyticsWarning[]
  sources: BedolagaAnalyticsSources
}

export interface BedolagaAnalyticsForecastDay {
  date: string
  expected_kopeks: number
  payments_count: number
}

export interface BedolagaAnalyticsForecastTariff {
  tariff_id: number | null
  tariff_name: string
  expected_kopeks: number
  payments_count: number
  unknown_count: number
}

export interface BedolagaAnalyticsForecastItem {
  user_id: number | null
  username: string
  subscription_id: number | null
  tariff_id: number | null
  tariff_name: string
  period_days: number
  period_price_kopeks: number | null
  end_date: string | null
  expected_charge_date: string | null
  autopay_enabled: boolean
  autopay_days_before: number | null
  amount_kopeks: number | null
  price_known: boolean
  price_source: string
}

export interface BedolagaAnalyticsForecast {
  month: string
  basis: string
  totals: {
    expected_kopeks: number
    expected_rubles: number
    payments_count: number
    unknown_count: number
    autopay_enabled_count: number
  }
  by_day: BedolagaAnalyticsForecastDay[]
  by_tariff: BedolagaAnalyticsForecastTariff[]
  items: BedolagaAnalyticsForecastItem[]
  items_total: number
  generated_at: string
  as_of: string
  partial: boolean
  warnings: BedolagaAnalyticsWarning[]
  sources: BedolagaAnalyticsSources
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

  // Revenue analytics (prices, customer finance)
  getAnalyticsTariffs: (params: Record<string, string> = {}) =>
    api.get<BedolagaAnalyticsTariffs>('/bedolaga/analytics/tariffs', { params }).then(r => r.data),
  getAnalyticsCustomer: (userId: number, params: Record<string, string> = {}) =>
    api.get<BedolagaAnalyticsCustomer>(`/bedolaga/analytics/customers/${userId}`, { params }).then(r => r.data),
  getAnalyticsOverview: (month?: string, basis: 'cash' | 'accrual' = 'cash', months = 6) =>
    api.get<BedolagaAnalyticsOverview>('/bedolaga/analytics/overview', { params: { month, basis, months } }).then(r => r.data),
  getAnalyticsForecast: (month?: string, basis: 'cash' | 'renewal' = 'cash') =>
    api.get<BedolagaAnalyticsForecast>('/bedolaga/analytics/forecast', { params: { month, basis } }).then(r => r.data),

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