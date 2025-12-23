import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import axios from 'axios'

interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  service: string
  source: string
}

interface Alert {
  type: string
  data: {
    title: string
    message: string
    level: string
    timestamp: string
  }
}

// Konfiguracja axios z timeout
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
  const connectionStatus = ref('disconnected')
  const lastUpdate = ref('')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Filtry
  const filters = reactive({
    level: '',
    service: '',
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

  // WebSocket
  let ws: WebSocket | null = null

  // Actions
  const fetchLogs = async () => {
    isLoading.value = true
    error.value = null
    try {
      const params = new URLSearchParams({
        page: pagination.page.toString(),
        size: pagination.size.toString(),
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value !== '')
        )
      })

      const response = await api.get(`/logs?${params}`)
      const data = response.data

      logs.value = data.logs
      pagination.total = data.total
      pagination.totalPages = data.pages || Math.ceil(data.total / pagination.size)

      lastUpdate.value = new Date().toLocaleTimeString()
    } catch (err: any) {
      error.value = `Failed to fetch logs: ${err.message}`
      console.error('Error fetching logs:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchStats = async () => {
    try {
      const response = await api.get('/logs/stats')
      return response.data
    } catch (err: any) {
      error.value = `Failed to fetch stats: ${err.message}`
      console.error('Error fetching stats:', err)
      return null
    }
  }

  const fetchMetadata = async () => {
    error.value = null
    try {
      const [levelsResponse, servicesResponse] = await Promise.all([
        api.get('/logs/levels'),
        api.get('/logs/services')
      ])

      availableLevels.value = levelsResponse.data.levels
      availableServices.value = servicesResponse.data.services
    } catch (err: any) {
      error.value = `Failed to fetch metadata: ${err.message}`
      console.error('Error fetching metadata:', err)
    }
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
        }

        if (message.type === 'alert') {
          alerts.value.unshift(message)

          setTimeout(() => {
            alerts.value = alerts.value.filter(a => a !== message)
          }, 30000)
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

  return {
    // State
    logs,
    alerts,
    availableLevels,
    availableServices,
    connectionStatus,
    lastUpdate,
    isLoading,
    error,
    filters,
    pagination,

    // Actions
    fetchLogs,
    fetchStats,
    fetchMetadata,
    connectWebSocket,
    clearFilters,
    nextPage,
    prevPage,
    clearError
  }
})