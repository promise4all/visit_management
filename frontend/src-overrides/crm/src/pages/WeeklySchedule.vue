<template>
  <div class="p-4 space-y-4">
    <h1 class="text-xl font-semibold">Weekly Schedule</h1>
    <div class="flex gap-2">
      <button class="px-3 py-1 border rounded" @click="load" :disabled="rows.loading">
        {{ rows.loading ? 'Loading…' : 'Reload' }}
      </button>
      <button class="px-3 py-1 border rounded" @click="createVisits" :disabled="createPlannedVisits.loading">
        {{ createPlannedVisits.loading ? 'Creating…' : 'Create Planned Visits' }}
      </button>
    </div>
    <div v-if="rows.loading" class="text-gray-600">Loading schedule…</div>
    <div v-else class="space-y-2">
      <div v-for="r in rows.data || []" :key="r.name" class="border rounded p-3 flex justify-between items-center">
        <div class="text-sm">
          <div class="font-medium">{{ r.client }} • {{ r.purpose }}</div>
          <div class="text-gray-600">{{ r.day }} {{ r.time_slot }}</div>
          <div class="text-gray-500" v-if="r.status">Status: {{ r.status }}</div>
        </div>
        <button v-if="r.docstatus !== 1 && r.status !== 'Approved'" class="px-2 py-1 border rounded text-xs" @click="approve(r.name)" :disabled="approveRow.loading">Approve</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useWeeklySchedule } from '@/composables/useWeeklySchedule'
const { rows, load, approveRow, createPlannedVisits } = useWeeklySchedule()

function approve(name) {
  approveRow.update({ params: { name } }); approveRow.fetch()
}
function createVisits() {
  createPlannedVisits.fetch()
}
</script>
