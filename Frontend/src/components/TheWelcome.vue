<template>
  <div class="logs-container">
    <h1>Intelligent Log Manager</h1>

    <!-- Filtry -->
    <div class="filters">
      <select v-model="filters.level">
        <option value="">Wszystkie poziomy</option>
        <option value="ERROR">ERROR</option>
        <option value="WARN">WARN</option>
        <option value="INFO">INFO</option>
        <option value="DEBUG">DEBUG</option>
      </select>

      <input
        v-model="filters.service"
        placeholder="Filtruj po serwisie"
      />

      <input
        type="date"
        v-model="filters.date_from"
        placeholder="Data od"
      />
      <input
        type="date"
        v-model="filters.date_to"
        placeholder="Data do"
      />

      <button @click="fetchLogs">Filtruj</button>
    </div>

    <!-- Tabela logów -->
    <div class="logs-table">
      <table>
        <thead>
          <tr>
            <th>Data</th>
            <th>Poziom</th>
            <th>Serwis</th>
            <th>Wiadomość</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.id"
            :class="`log-level-${log.level.toLowerCase()}`"
          >
            <td>{{ new Date(log.timestamp).toLocaleString() }}</td>
            <td class="level-badge">{{ log.level }}</td>
            <td>{{ log.service }}</td>
            <td>{{ log.message }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Paginacja -->
    <div class="pagination">
      <button
        @click="prevPage"
        :disabled="page === 1"
      >
        Poprzednia
      </button>
      <span>Strona {{ page }} z {{ totalPages }}</span>
      <button
        @click="nextPage"
        :disabled="page >= totalPages"
      >
        Następna
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'

interface LogEntry {
  id: string
  timestamp: string
  level: string
  message: string
  service: string
  source: string
}

const logs = ref<LogEntry[]>([])
const page = ref(1)
const size = ref(50)
const total = ref(0)

const filters = reactive({
  level: '',
  service: '',
  date_from: '',
  date_to: ''
})

const totalPages = computed(() => Math.ceil(total.value / size.value))

const fetchLogs = async () => {
  try {
    const params = new URLSearchParams({
      page: page.value.toString(),
      size: size.value.toString(),
      ...Object.fromEntries(
        Object.entries(filters).filter(([_, value]) => value !== '')
      )
    })

    const response = await fetch(`http://localhost:8000/logs?${params}`)
    const data = await response.json()

    logs.value = data.logs
    total.value = data.total
  } catch (error) {
    console.error('Błąd przy pobieraniu logów:', error)
  }
}

const nextPage = () => {
  page.value++
  fetchLogs()
}

const prevPage = () => {
  if (page.value > 1) {
    page.value--
    fetchLogs()
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.logs-container {
  padding: 20px;
}

.filters {
  margin-bottom: 20px;
}

.filters select, .filters input {
  margin-right: 10px;
  padding: 5px;
}

.logs-table {
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

th {
  background-color: #f2f2f2;
}

.level-badge {
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 3px;
}

.log-level-error .level-badge {
  background-color: #ffebee;
  color: #c62828;
}

.log-level-warn .level-badge {
  background-color: #fff3e0;
  color: #ef6c00;
}

.log-level-info .level-badge {
  background-color: #e3f2fd;
  color: #1565c0;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}
</style>