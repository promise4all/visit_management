<template>
  <div class="p-4 space-y-4">
    <h1 class="text-xl font-semibold">Visits</h1>

    <div class="flex gap-2 items-end">
      <div>
        <label class="block text-sm text-gray-600">Status</label>
        <select v-model="status" class="border rounded px-2 py-1">
          <option value="">All</option>
          <option>Planned</option>
          <option>In Progress</option>
          <option>Completed</option>
          <option>Cancelled</option>
        </select>
      </div>
      <button class="px-3 py-1 border rounded" @click="reload">Apply</button>
    </div>

    <div v-if="list.loading" class="text-gray-600">Loading…</div>
    <div v-else class="space-y-2">
      <div v-for="v in list.data || []" :key="v.name" class="border rounded p-3 flex justify-between items-center">
        <div>
          <div class="font-medium">{{ v.name }}</div>
          <div class="text-sm text-gray-600">{{ v.client_type }} • {{ v.client }} • {{ v.status }}</div>
        </div>
        <router-link class="text-primary-600 hover:underline" :to="{ name: 'Visit', params: { visitId: v.name } }">Open</router-link>
      </div>

      <div class="flex gap-2">
        <button class="px-3 py-1 border rounded" @click="prevPage" :disabled="pagination.start===0">Prev</button>
        <button class="px-3 py-1 border rounded" @click="nextPage">Next</button>
      </div>
    </div>
  </div>
  
</template>

<script setup>
import { ref, watch } from 'vue'
import { useVisits } from '@/composables/useVisits'

const { list, setFilter, nextPage, prevPage, pagination } = useVisits()
const status = ref('')

function reload() {
  setFilter('status', status.value || undefined)
}

watch(status, reload)
</script>
