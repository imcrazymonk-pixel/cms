import axios from 'axios'

const adminApi = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
})

adminApi.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-store')
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (parsed.state?.token) {
        config.headers.Authorization = `Bearer ${parsed.state.token}`
      }
    } catch { /* ignore */ }
  }
  return config
})

adminApi.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth-store')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export interface PingEntry {
  ms: number | null
  loss: number | null
}

export interface NodeTCP {
  retrans_pct?: number | null
  timeouts?: number
  in_segs?: number
  out_segs?: number
}

export interface NodeNetworkErrors {
  rx_err?: number
  tx_err?: number
}

export interface NodeLoad {
  '1m'?: number
  '5m'?: number
  '15m'?: number
}

export interface NodeRAM {
  used?: string
  total?: string
}

export interface NodeDisk {
  used?: string
  total?: string
  pct?: string
}

export interface NodeDockerContainer {
  name: string
}

export interface NodeNginx {
  status?: string
  error?: string
}

export interface NodeCert {
  [key: string]: unknown
}

export interface NodeData {
  hostname?: string
  uptime?: string
  cpu_cores?: number
  load?: NodeLoad
  ram?: NodeRAM
  disk?: NodeDisk
  docker?: NodeDockerContainer[]
  nginx?: NodeNginx
  speed_download_mbps?: number | null
  tcp?: NodeTCP
  network_errors?: NodeNetworkErrors
  pings?: Record<string, PingEntry>
  certs?: NodeCert[]
}

export interface Node {
  id: string
  name: string
  reachable: boolean
  error?: string
  data?: NodeData
}

export interface DiagnosticsSummary {
  total: number
  reachable: number
  unreachable: number
  problems: number
  avgLoad: number
}

export interface DiagnosticsData {
  success: boolean
  collected_at: string | null
  nodes: Node[]
  summary: DiagnosticsSummary
  is_collecting: boolean
}

export const diagnosticsApi = {
  getData: () =>
    adminApi.get<DiagnosticsData>('/admin/diagnostics/api/data').then(r => r.data),

  collect: () =>
    adminApi.post<{ success: boolean; message?: string; error?: string }>('/admin/diagnostics/api/collect').then(r => r.data),
}