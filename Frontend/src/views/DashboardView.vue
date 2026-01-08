<template>
  <div class="dashboard">
    <!-- Nagłówek -->
    <div class="dashboard-header">
      <div class="header-left">
        <h1>🪵 Intelligent Log Manager</h1>
        <p class="subtitle">Multi-source log aggregation and analysis</p>
      </div>
      <div class="status-indicators">
        <div class="status-item">
          <span class="status-label">WebSocket:</span>
          <span class="status-value" :class="logStore.connectionStatus">
            {{ logStore.connectionStatus }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">Last update:</span>
          <span class="status-value">{{ logStore.lastUpdate }}</span>
        </div>
      </div>
    </div>

    <!-- Statystyki -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value">{{ logStore.stats.totalLogs }}</div>
        <div class="stat-title">Total Logs</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🚨</div>
        <div class="stat-value">{{ logStore.stats.errorsLastHour }}</div>
        <div class="stat-title">Errors (1h)</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔧</div>
        <div class="stat-value">{{ logStore.stats.uniqueServices }}</div>
        <div class="stat-title">Services</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📁</div>
        <div class="stat-value">{{ logStore.availableSources.length }}</div>
        <div class="stat-title">Active Sources</div>
      </div>
    </div>

    <!-- Panel źródeł -->
    <div class="sources-panel">
      <h3>🔌 Log Sources</h3>
      <div class="sources-grid">
        <div
          v-for="source in logStore.sourcesConfig"
          :key="source.name"
          class="source-item"
          :class="{ 'source-disabled': !source.enabled }"
          @click="toggleSource(source.name)"
          :title="source.description || source.name"
        >
          <div class="source-icon">
            {{ logStore.getSourceIcon(source.type) }}
          </div>
          <div class="source-info">
            <div class="source-name">{{ source.name }}</div>
            <div class="source-type">{{ source.type }}</div>
          </div>
          <div class="source-toggle">
            <span class="toggle-indicator" :class="{ 'active': source.enabled }"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Alerty -->
    <div class="alerts-panel" v-if="logStore.alerts.length > 0">
      <h3>🚨 Active Alerts</h3>
      <div
        v-for="alert in logStore.alerts"
        :key="alert.data.timestamp"
        class="alert-item"
        :class="`alert-${alert.data.level.toLowerCase()}`"
      >
        <strong>{{ alert.data.title }}</strong>
        <span>{{ alert.data.message }}</span>
        <small>{{ new Date(alert.data.timestamp).toLocaleTimeString() }}</small>
      </div>
    </div>

    <!-- Błędy -->
    <div v-if="logStore.error" class="error-panel">
      <div class="error-content">
        <span class="error-message">{{ logStore.error }}</span>
        <button @click="logStore.clearError" class="error-close">×</button>
      </div>
    </div>

    <!-- Filtry -->
    <div class="filters-panel">
      <div class="filter-group">
        <label>Source:</label>
        <select v-model="logStore.filters.source" @change="onSourceChange">
          <option value="">All Sources</option>
          <option
            v-for="source in logStore.availableSources"
            :key="source"
            :value="source"
          >
            {{ source }}
            <template v-if="logStore.getSourceConfig(source)">
              {{ logStore.getSourceIcon(logStore.getSourceConfig(source)!.type) }}
            </template>
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Level:</label>
        <select v-model="logStore.filters.level" @change="onFilterChange">
          <option value="">All Levels</option>
          <option v-for="level in logStore.availableLevels" :key="level" :value="level">
            {{ level }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Service:</label>
        <select v-model="logStore.filters.service" @change="onFilterChange">
          <option value="">All Services</option>
          <option v-for="service in logStore.availableServices" :key="service" :value="service">
            {{ service }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Date From:</label>
        <input type="datetime-local" v-model="logStore.filters.date_from" @change="onFilterChange">
      </div>

      <div class="filter-group">
        <label>Date To:</label>
        <input type="datetime-local" v-model="logStore.filters.date_to" @change="onFilterChange">
      </div>

      <div class="filter-group search-group">
        <label>Search:</label>
        <input
          type="text"
          v-model="logStore.filters.search_text"
          placeholder="Search in messages..."
          @input="onSearchInput"
        >
      </div>

      <div class="filter-actions">
        <button @click="logStore.clearFilters" class="clear-btn">
          <span class="btn-icon">🗑️</span>
          Clear Filters
        </button>
        <button @click="clearAllLogs" class="clear-logs-btn">
          <span class="btn-icon">🧹</span>
          Clear Logs
        </button>
        <button @click="refreshLogs" class="refresh-btn" :disabled="logStore.isLoading">
          <span class="btn-icon" v-if="!logStore.isLoading">🔄</span>
          <span class="btn-icon loading" v-else>⏳</span>
          {{ logStore.isLoading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Tabela logów -->
    <div class="logs-section">
      <div class="section-header">
        <h2>📝 Application Logs</h2>
        <div class="section-info">
          <span class="info-item">
            Showing {{ logStore.logs.length }} of {{ logStore.pagination.total }} logs
          </span>
          <span class="info-item">
            Sources: {{ logStore.filters.source || 'All' }}
          </span>
        </div>
      </div>

      <div class="logs-table-container">
        <table class="logs-table">
          <thead>
            <tr>
              <th @click="sortBy('timestamp')" class="sortable">
                Timestamp {{ sortIcon('timestamp') }}
              </th>
              <th @click="sortBy('source')" class="sortable">
                Source {{ sortIcon('source') }}
              </th>
              <th @click="sortBy('level')" class="sortable">
                Level {{ sortIcon('level') }}
              </th>
              <th @click="sortBy('service')" class="sortable">
                Service {{ sortIcon('service') }}
              </th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="log in sortedLogs"
              :key="log.id"
              :class="`log-level-${log.level.toLowerCase()}`"
              @click="selectLog(log)"
              :title="`Click to view details\nSource: ${log.source}\nRaw data available: ${!!log.original_data}`"
            >
              <td class="timestamp">
                {{ new Date(log.timestamp).toLocaleString() }}
              </td>
              <td class="source-cell">
                <span
                  class="source-badge"
                  :style="{ backgroundColor: logStore.getSourceColor(log.source) }"
                  :title="log.source"
                >
                  {{ logStore.getSourceIcon(log.source) }} {{ log.source }}
                </span>
              </td>
              <td class="level">
                <span class="level-badge">{{ log.level }}</span>
              </td>
              <td class="service">{{ log.service }}</td>
              <td class="message">
                <div class="message-content">
                  {{ truncateMessage(log.message) }}
                  <span v-if="log.original_data" class="raw-data-indicator" title="Raw data available">
                    📋
                  </span>
                </div>
              </td>
            </tr>
            <tr v-if="logStore.logs.length === 0 && !logStore.isLoading">
              <td colspan="5" class="no-logs">
                <div class="empty-state">
                  <span class="empty-icon">📭</span>
                  <p>No logs found</p>
                  <small v-if="logStore.filters.source">Try changing source filter or enabling more sources</small>
                </div>
              </td>
            </tr>
            <tr v-if="logStore.isLoading">
              <td colspan="5" class="loading-row">
                <div class="loading-spinner"></div>
                <span>Loading logs...</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginacja -->
      <div class="pagination">
        <button
          @click="logStore.prevPage"
          :disabled="logStore.pagination.page === 1 || logStore.isLoading"
          class="pagination-btn"
        >
          ← Previous
        </button>

        <div class="page-info">
          <span class="page-current">Page {{ logStore.pagination.page }}</span>
          <span class="page-total">of {{ logStore.pagination.totalPages }}</span>
          <span class="page-total-logs">({{ logStore.pagination.total }} total)</span>
        </div>

        <button
          @click="logStore.nextPage"
          :disabled="logStore.pagination.page >= logStore.pagination.totalPages || logStore.isLoading"
          class="pagination-btn"
        >
          Next →
        </button>
      </div>
    </div>

    <!-- Modal z detalami logu -->
    <div v-if="selectedLog" class="modal-overlay" @click="selectedLog = null">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Log Details</h3>
          <button @click="selectedLog = null" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-grid">
            <div class="detail-item">
              <label>Timestamp:</label>
              <span>{{ new Date(selectedLog.timestamp).toLocaleString() }}</span>
            </div>
            <div class="detail-item">
              <label>Source:</label>
              <span class="source-badge" :style="{ backgroundColor: logStore.getSourceColor(selectedLog.source) }">
                {{ logStore.getSourceIcon(selectedLog.source) }} {{ selectedLog.source }}
              </span>
            </div>
            <div class="detail-item">
              <label>Level:</label>
              <span class="level-badge">{{ selectedLog.level }}</span>
            </div>
            <div class="detail-item">
              <label>Service:</label>
              <span>{{ selectedLog.service }}</span>
            </div>
            <div class="detail-item full-width">
              <label>Message:</label>
              <pre class="message-pre">{{ selectedLog.message }}</pre>
            </div>
            <div v-if="selectedLog.original_data" class="detail-item full-width">
              <label>Raw Data:</label>
              <pre class="raw-data">{{ JSON.stringify(selectedLog.original_data, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue'
import { useLogStore } from '@/stores/logstore'

const logStore = useLogStore()
const selectedLog = ref<any>(null)
const sortField = ref('timestamp')
const sortDirection = ref('desc')

let searchTimeout: number

// Funkcja do czyszczenia wszystkich logów
const clearAllLogs = () => {
  if (confirm('Are you sure you want to clear all displayed logs?')) {
    logStore.clearLogs()
    logStore.pagination.page = 1
    logStore.pagination.total = 0
    logStore.pagination.totalPages = 0
  }
}

// Funkcja do odświeżania logów z czyszczeniem
const refreshLogs = () => {
  logStore.pagination.page = 1
  logStore.clearLogs()
  logStore.fetchLogs()
}

// Funkcja do zmiany źródła
const onSourceChange = () => {
  logStore.pagination.page = 1
  logStore.clearLogs()
  logStore.fetchLogs()
}

// Funkcja do zmiany filtrów
const onFilterChange = () => {
  logStore.pagination.page = 1
  logStore.clearLogs()
  logStore.fetchLogs()
}

// Funkcja do przełączania źródła z potwierdzeniem
const toggleSource = (sourceName: string) => {
  const source = logStore.sourcesConfig.find(s => s.name === sourceName)
  if (source && source.enabled) {
    // Jeśli wyłączamy źródło, zapytaj o potwierdzenie
    if (confirm(`Disable ${sourceName} source? This will clear current logs.`)) {
      logStore.toggleSource(sourceName)
    }
  } else {
    logStore.toggleSource(sourceName)
  }
}

const onSearchInput = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    logStore.pagination.page = 1
    logStore.clearLogs()
    logStore.fetchLogs()
  }, 500)
}

const sortedLogs = computed(() => {
  const logs = [...logStore.logs]
  return logs.sort((a: any, b: any) => {
    let aVal = a[sortField.value]
    let bVal = b[sortField.value]

    if (sortField.value === 'timestamp') {
      aVal = new Date(a.timestamp).getTime()
      bVal = new Date(b.timestamp).getTime()
    }

    if (sortDirection.value === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })
})

const sortBy = (field: string) => {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'asc'
  }
}

const sortIcon = (field: string) => {
  if (sortField.value !== field) return '↕️'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}

const truncateMessage = (message: string, length: number = 100) => {
  return message.length > length ? message.substring(0, length) + '...' : message
}

const selectLog = (log: any) => {
  selectedLog.value = log
}

onMounted(async () => {
  await logStore.fetchMetadata()
  await logStore.fetchLogs()
  await logStore.fetchStats()
  logStore.connectWebSocket()
})

// Watch for WebSocket connection
watch(
  () => logStore.connectionStatus,
  (newStatus) => {
    if (newStatus === 'connected') {
      logStore.fetchLogs()
      logStore.fetchStats()
    }
  }
)

// Watch for source toggles
watch(
  () => logStore.availableSources,
  () => {
    logStore.fetchLogs()
  }
)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e1e5e9;
}

.header-left h1 {
  margin: 0;
  color: #2c3e50;
}

.subtitle {
  margin: 0.25rem 0 0 0;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.status-indicators {
  display: flex;
  gap: 1.5rem;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.status-label {
  font-size: 0.8rem;
  color: #7f8c8d;
}

.status-value {
  font-weight: 600;
}

.status-value.connected {
  color: #27ae60;
}

.status-value.disconnected {
  color: #e74c3c;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
  border-top: 4px solid #3498db;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: bold;
  color: #2c3e50;
  margin: 0.25rem 0;
}

.stat-title {
  color: #7f8c8d;
  font-size: 0.85rem;
}

/* Sources Panel */
.sources-panel {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.sources-panel h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
}

.source-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #f8f9fa;
}

.source-item:hover {
  border-color: #3498db;
  background: #fff;
  box-shadow: 0 2px 6px rgba(52, 152, 219, 0.2);
}

.source-item.source-disabled {
  opacity: 0.5;
  background: #f5f5f5;
}

.source-icon {
  font-size: 1.25rem;
  margin-right: 0.75rem;
}

.source-info {
  flex: 1;
}

.source-name {
  font-weight: 600;
  color: #2c3e50;
}

.source-type {
  font-size: 0.75rem;
  color: #7f8c8d;
  text-transform: uppercase;
}

.source-toggle {
  margin-left: 0.5rem;
}

.toggle-indicator {
  display: block;
  width: 24px;
  height: 14px;
  background: #bdc3c7;
  border-radius: 7px;
  position: relative;
  transition: background 0.2s;
}

.toggle-indicator.active {
  background: #27ae60;
}

.toggle-indicator::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  background: white;
  border-radius: 50%;
  top: 1px;
  left: 1px;
  transition: transform 0.2s;
}

.toggle-indicator.active::after {
  transform: translateX(10px);
}

/* Alerts */
.alerts-panel {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  padding: 1rem;
}

.alert-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  margin: 0.5rem 0;
  background: white;
  border-radius: 4px;
  border-left: 4px solid #f39c12;
}

.alert-item.alert-critical {
  border-left-color: #e74c3c !important;
  background: #ffeaea !important;
}

/* Errors */
.error-panel {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 8px;
  padding: 0.75rem;
  color: #721c24;
}

.error-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #721c24;
}

/* Filters */
.filters-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  padding: 1.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.filter-group label {
  font-weight: 600;
  font-size: 0.8rem;
  color: #2c3e50;
}

.filter-group select,
.filter-group input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #bdc3c7;
  border-radius: 6px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.filter-group select:focus,
.filter-group input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.search-group {
  grid-column: span 2;
}

.filter-actions {
  grid-column: span 2;
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.clear-btn,
.clear-logs-btn,
.refresh-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s;
}

.clear-btn {
  background: #e74c3c;
  color: white;
}

.clear-btn:hover {
  background: #c0392b;
}

.clear-logs-btn {
  background: #e67e22;
  color: white;
}

.clear-logs-btn:hover {
  background: #d35400;
}

.refresh-btn {
  background: #3498db;
  color: white;
}

.refresh-btn:hover:not(:disabled) {
  background: #2980b9;
}

.refresh-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 0.9rem;
}

.btn-icon.loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Logs Table */
.logs-section {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.section-header {
  padding: 1.25rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e1e5e9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h2 {
  margin: 0;
  color: #2c3e50;
}

.section-info {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.logs-table-container {
  overflow-x: auto;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
}

.logs-table th {
  background: #34495e;
  color: white;
  padding: 0.875rem 1rem;
  text-align: left;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.logs-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.logs-table th.sortable:hover {
  background: #2c3e50;
}

.logs-table td {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #ecf0f1;
  font-size: 0.9rem;
}

.logs-table tbody tr {
  cursor: pointer;
  transition: background 0.2s;
}

.logs-table tbody tr:hover {
  background: #f8f9fa;
}

.timestamp {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.8rem;
  color: #7f8c8d;
  white-space: nowrap;
}

.source-cell {
  white-space: nowrap;
}

.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.level-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.log-level-error .level-badge {
  background: #e74c3c;
  color: white;
}

.log-level-warn .level-badge {
  background: #f39c12;
  color: white;
}

.log-level-info .level-badge {
  background: #3498db;
  color: white;
}

.log-level-debug .level-badge {
  background: #95a5a6;
  color: white;
}

.service {
  font-weight: 600;
  color: #2c3e50;
}

.message-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.raw-data-indicator {
  opacity: 0.6;
  font-size: 0.8rem;
}

.no-logs, .loading-row {
  text-align: center;
  padding: 3rem !important;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #7f8c8d;
}

.empty-icon {
  font-size: 2rem;
  opacity: 0.5;
}

.loading-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.loading-spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid #bdc3c7;
  border-top-color: #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #ecf0f1;
}

.page-info {
  display: flex;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #7f8c8d;
}

.page-current {
  font-weight: 600;
  color: #2c3e50;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #2980b9;
}

.pagination-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  padding: 1.25rem 1.5rem;
  background: #34495e;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  max-height: calc(80vh - 70px);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item.full-width {
  grid-column: span 2;
}

.detail-item label {
  font-weight: 600;
  font-size: 0.8rem;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.message-pre {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.9rem;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.raw-data {
  background: #2c3e50;
  color: #ecf0f1;
  padding: 1rem;
  border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.8rem;
  overflow-x: auto;
  max-height: 200px;
  margin: 0;
}

/* Responsywność */
@media (max-width: 1200px) {
  .filters-panel {
    grid-template-columns: repeat(3, 1fr);
  }

  .search-group,
  .filter-actions {
    grid-column: span 3;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 1rem;
  }

  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .status-indicators {
    width: 100%;
    justify-content: space-between;
  }

  .status-item {
    align-items: flex-start;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filters-panel {
    grid-template-columns: 1fr;
  }

  .search-group,
  .filter-actions {
    grid-column: 1;
  }

  .filter-actions {
    flex-direction: column;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .section-info {
    flex-direction: column;
    gap: 0.25rem;
  }

  .pagination {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>