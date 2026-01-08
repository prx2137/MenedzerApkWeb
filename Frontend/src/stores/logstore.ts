import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import axios from 'axios'

// Eksportowane interfejsy
export interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  service: string
  source: string
  original_data?: any
}

export interface Alert {
  type: string
  data: {
    title: string
    message: string
    level: string
    timestamp: string
  }
}

export interface SourceConfig {
  name: string
  type: string
  enabled: boolean
  description?: string
}

// Konfiguracja axios
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})

export const useLogStore = defineStore('logs', () => {
  // State
  const logs = ref<LogEntry[]>([])
  const alerts = ref<Alert[]>([])
  const availableLevels = ref<string[]>([])
  const availableServices = ref<string[]>([])
  const availableSources = ref<string[]>([])
  const connectionStatus = ref('disconnected')
  const lastUpdate = ref('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Konfiguracja źródeł (można rozszerzyć o pobieranie z API)
  const sourcesConfig = ref<SourceConfig[]>([
    { name: 'file', type: 'file', enabled: true, description: 'Pliki logów' },
    { name: 'api', type: 'api', enabled: true, description: 'API logów' },
    { name: 'database', type: 'database', enabled: true, description: 'Baza danych' },
    { name: 'elasticsearch', type: 'elasticsearch', enabled: true, description: 'Elasticsearch' }
  ])

  // Filtry
  const filters = reactive({
    level: '',
    service: '',
    source: '',
    date_from: '',
    date_to: '',
    search_text: ''
  })

  // Paginacja
  const pagination = reactive({
    page: 1,
    size: 50,
    total: 0,
    totalPages: 0
  })

  // Statystyki
  const stats = reactive({
    totalLogs: 0,
    errorsLastHour: 0,
    uniqueServices: 0,
    uniqueSources: 0
  })

  // WebSocket
  let ws: WebSocket | null = null

  // Actions
 const fetchLogs = async () => {
  isLoading.value = true
  error.value = null
  try {
    // Stwórz kopię filtrów bez pustych wartości
    const activeFilters: Record<string, string> = {}

    Object.entries(filters).forEach(([key, value]) => {
      if (value && value !== '') {
        activeFilters[key] = value
      }
    })

    const params = new URLSearchParams({
      page: pagination.page.toString(),
      size: pagination.size.toString(),
      ...activeFilters
    })

    const response = await api.get(`/logs?${params}`)
    const data = response.data

    // Zawsze nadpisuj logi nowymi danymi
    logs.value = data.logs || []
    pagination.total = data.total || 0
    pagination.totalPages = data.pages || Math.ceil((data.total || 0) / pagination.size)

    lastUpdate.value = new Date().toLocaleTimeString()

    // Jeśli są źródła w odpowiedzi, zaktualizuj dostępne źródła
    if (data.sources && data.sources.length > 0) {
      availableSources.value = data.sources
    }

  } catch (err: any) {
    error.value = `Failed to fetch logs: ${err.message}`
    console.error('Error fetching logs:', err)
    // W przypadku błędu wyczyść logi
    logs.value = []
    pagination.total = 0
    pagination.totalPages = 0
  } finally {
    isLoading.value = false
  }
}


  const clearLogs = () => {
  logs.value = []
}

// Popraw funkcję toggleSource:
const toggleSource = (sourceName: string) => {
  const source = sourcesConfig.value.find(s => s.name === sourceName)
  if (source) {
    source.enabled = !source.enabled

    // Odśwież listę dostępnych źródeł
    availableSources.value = sourcesConfig.value
      .filter(s => s.enabled)
      .map(s => s.name)

    // Jeśli wyłączono aktualnie wybrane źródło, wyczyść filtr
    if (filters.source === sourceName && !source.enabled) {
      filters.source = ''
    }

    // Wyczyść logi i pobierz nowe
    clearLogs()  // Dodaj to!
    fetchLogs()  // Odśwież logi
  }
}

  const fetchStats = async () => {
    try {
      const response = await api.get('/logs/stats')
      const data = response.data

      stats.totalLogs = data.total_logs
      stats.errorsLastHour = data.recent_errors
      stats.uniqueServices = data.service_stats.length
      stats.uniqueSources = data.source_stats?.length || 0

      return data
    } catch (err: any) {
      error.value = `Failed to fetch stats: ${err.message}`
      console.error('Error fetching stats:', err)
      return null
    }
  }

  const fetchMetadata = async () => {
    error.value = null
    try {
      const [levelsResponse, servicesResponse, sourcesResponse] = await Promise.all([
        api.get('/logs/levels'),
        api.get('/logs/services'),
        api.get('/logs/sources') // Nowy endpoint
      ])

      availableLevels.value = levelsResponse.data.levels
      availableServices.value = servicesResponse.data.services
      availableSources.value = sourcesResponse.data.sources || []

      // Jeśli nie ma endpointu sources, użyj domyślnych
      if (!sourcesResponse.data.sources) {
        availableSources.value = sourcesConfig.value
          .filter(source => source.enabled)
          .map(source => source.name)
      }

    } catch (err: any) {
      error.value = `Failed to fetch metadata: ${err.message}`
      console.error('Error fetching metadata:', err)

      // Fallback: użyj domyślnych źródeł
      availableSources.value = sourcesConfig.value
        .filter(source => source.enabled)
        .map(source => source.name)
    }
  }

  const getSourceConfig = (sourceName: string): SourceConfig | undefined => {
    return sourcesConfig.value.find(s => s.name === sourceName)
  }

  const getSourceIcon = (sourceType: string): string => {
    const icons: Record<string, string> = {
      'file': '📄',
      'api': '🔌',
      'database': '🗄️',
      'elasticsearch': '🔍',
      'system': '⚙️',
      'docker': '🐳',
      'kubernetes': '☸️'
    }
    return icons[sourceType] || '📊'
  }

  const getSourceColor = (sourceType: string): string => {
    const colors: Record<string, string> = {
      'file': '#3498db',
      'api': '#9b59b6',
      'database': '#2ecc71',
      'elasticsearch': '#e74c3c',
      'system': '#f39c12',
      'docker': '#1abc9c',
      'kubernetes': '#34495e'
    }
    return colors[sourceType] || '#95a5a6'
  }



  const connectWebSocket = () => {
    try {
      ws = new WebSocket('ws://localhost:8000/ws')

      ws.onopen = () => {
        connectionStatus.value = 'connected'
        console.log('WebSocket connected')
        error.value = null
      }

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)

        if (message.type === 'new_log') {
          logs.value.unshift({
            id: Date.now().toString(),
            ...message.data
          })

          if (logs.value.length > 1000) {
            logs.value = logs.value.slice(0, 500)
          }

          fetchStats() // Odśwież statystyki
        }

        if (message.type === 'alert') {
          alerts.value.unshift(message)

          setTimeout(() => {
            alerts.value = alerts.value.filter(a => a !== message)
          }, 30000)

          fetchStats()
        }
      }

      ws.onclose = () => {
        connectionStatus.value = 'disconnected'
        console.log('WebSocket disconnected')
        setTimeout(connectWebSocket, 5000)
      }

      ws.onerror = (err) => {
        console.error('WebSocket error:', err)
        connectionStatus.value = 'error'
        error.value = 'WebSocket connection failed'
      }
    } catch (err: any) {
      error.value = `WebSocket setup failed: ${err.message}`
    }
  }

  const clearFilters = () => {
    Object.keys(filters).forEach(key => {
      filters[key as keyof typeof filters] = ''
    })
    pagination.page = 1
    fetchLogs()
  }

  const nextPage = () => {
    if (pagination.page < pagination.totalPages) {
      pagination.page++
      fetchLogs()
    }
  }

  const prevPage = () => {
    if (pagination.page > 1) {
      pagination.page--
      fetchLogs()
    }
  }

  const clearError = () => {
    error.value = null
  }

  const getSourceStats = async () => {
    try {
      const response = await api.get('/logs/stats/sources')
      return response.data
    } catch (err) {
      console.error('Error fetching source stats:', err)
      return {}
    }
  }

  return {
    // State
    logs,
    alerts,
    availableLevels,
    availableServices,
    availableSources,
    connectionStatus,
    lastUpdate,
    isLoading,
    error,
    filters,
    pagination,
    stats,
    sourcesConfig,



    // Actions
    fetchLogs,
    fetchStats,
    fetchMetadata,
    getSourceConfig,
    getSourceIcon,
    getSourceColor,
    toggleSource,
    connectWebSocket,
    clearFilters,
    nextPage,
    prevPage,
    clearError,
    getSourceStats,
    clearLogs
  }
})