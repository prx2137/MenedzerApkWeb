<template>
  <div class="dashboard">
    <!-- Nagłówek -->
    <div class="dashboard-header">
      <h1>📊 Log Dashboard</h1>
      <div class="status-indicators">
        <span class="status" :class="logStore.connectionStatus">
          {{ logStore.connectionStatus }}
        </span>
        <span class="last-update">
          Updated: {{ logStore.lastUpdate }}
        </span>
      </div>
    </div>

    <!-- Statystyki -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ logStore.pagination.total }}</div>
        <div class="stat-title">Total Logs</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ logStore.alerts.length }}</div>
        <div class="stat-title">Active Alerts</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ logStore.availableServices.length }}</div>
        <div class="stat-title">Services</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ logStore.availableLevels.length }}</div>
        <div class="stat-title">Log Levels</div>
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

    <!-- Filtry -->
    <div class="filters-panel">
      <div class="filter-group">
        <label>Level:</label>
        <select v-model="logStore.filters.level" @change="logStore.fetchLogs">
          <option value="">All Levels</option>
          <option v-for="level in logStore.availableLevels" :key="level" :value="level">
            {{ level }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Service:</label>
        <select v-model="logStore.filters.service" @change="logStore.fetchLogs">
          <option value="">All Services</option>
          <option v-for="service in logStore.availableServices" :key="service" :value="service">
            {{ service }}
          </option>
        </select>
      </div>

      <div class="filter-group">
        <label>Search:</label>
        <input
          type="text"
          v-model="logStore.filters.search_text"
          placeholder="Search messages..."
          @input="onSearchInput"
        >
      </div>

      <button @click="logStore.clearFilters" class="clear-btn">Clear Filters</button>
    </div>

    <!-- Tabela logów -->
    <div class="logs-section">
      <div class="section-header">
        <h2>Application Logs</h2>
        <button @click="logStore.fetchLogs" class="refresh-btn" :disabled="logStore.isLoading">
          {{ logStore.isLoading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>

      <div class="logs-table-container">
        <table class="logs-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Level</th>
              <th>Service</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="log in logStore.logs"
              :key="log.id"
              :class="`log-level-${log.level.toLowerCase()}`"
            >
              <td class="timestamp">
                {{ new Date(log.timestamp).toLocaleString() }}
              </td>
              <td class="level">
                <span class="level-badge">{{ log.level }}</span>
              </td>
              <td class="service">{{ log.service }}</td>
              <td class="message">{{ log.message }}</td>
            </tr>
            <tr v-if="logStore.logs.length === 0">
              <td colspan="4" class="no-logs">
                No logs found
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginacja -->
      <div class="pagination">
        <button
          @click="logStore.prevPage"
          :disabled="logStore.pagination.page === 1"
          class="pagination-btn"
        >
          Previous
        </button>

        <span class="page-info">
          Page {{ logStore.pagination.page }} of {{ logStore.pagination.totalPages }}
          ({{ logStore.pagination.total }} total logs)
        </span>

        <button
          @click="logStore.nextPage"
          :disabled="logStore.pagination.page >= logStore.pagination.totalPages"
          class="pagination-btn"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useLogStore } from '../stores/logStore'

const logStore = useLogStore()

let searchTimeout: number

const onSearchInput = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    logStore.pagination.page = 1
    logStore.fetchLogs()
  }, 500)
}

onMounted(async () => {
  await logStore.fetchLogs()
})

// Watch for WebSocket connection to load logs
watch(
  () => logStore.connectionStatus,
  (newStatus) => {
    if (newStatus === 'connected') {
      logStore.fetchLogs()
    }
  }
)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e1e5e9;
}

.status-indicators {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
}

.status.connected {
  color: #27ae60;
  font-weight: bold;
}

.status.disconnected {
  color: #e74c3c;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  text-align: center;
  border-left: 4px solid #3498db;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #2c3e50;
}

.stat-title {
  color: #7f8c8d;
  margin-top: 0.5rem;
}

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

.alert-critical {
  border-left-color: #e74c3c !important;
  background: #ffeaea !important;
}

.filters-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: end;
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-weight: bold;
  font-size: 0.8rem;
  color: #7f8c8d;
}

.filter-group select,
.filter-group input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #bdc3c7;
  border-radius: 4px;
  min-width: 150px;
}

.clear-btn, .refresh-btn {
  padding: 0.5rem 1rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  height: fit-content;
}

.refresh-btn {
  background: #3498db;
}

.clear-btn:hover {
  background: #c0392b;
}

.refresh-btn:hover:not(:disabled) {
  background: #2980b9;
}

.refresh-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.logs-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e1e5e9;
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
  padding: 1rem;
  text-align: left;
  font-weight: 600;
}

.logs-table td {
  padding: 1rem;
  border-bottom: 1px solid #ecf0f1;
}

.logs-table tbody tr:hover {
  background: #f8f9fa;
}

.timestamp {
  font-family: monospace;
  font-size: 0.8rem;
  color: #7f8c8d;
  white-space: nowrap;
}

.level-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
  text-transform: uppercase;
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

.message {
  max-width: 400px;
  word-wrap: break-word;
}

.no-logs {
  text-align: center;
  color: #7f8c8d;
  font-style: italic;
  padding: 2rem;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #ecf0f1;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.page-info {
  color: #7f8c8d;
  font-size: 0.9rem;
}

/* Responsywność */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .filters-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    min-width: auto;
  }

  .pagination {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
}
</style>