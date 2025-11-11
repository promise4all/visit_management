<template>
  <div class="p-4 space-y-4">
    <h1 class="text-xl font-semibold">Visit: {{ visitId }}</h1>

    <div v-if="visit.loading" class="text-gray-600">Loading…</div>
    <div v-else-if="!visit.data" class="text-gray-600">No data.</div>
    <div v-else class="space-y-2">
      <div class="text-sm text-gray-700">
        <div><b>Status:</b> {{ visit.data.status }}</div>
        <div><b>Client:</b> {{ visit.data.client_type }} • {{ visit.data.client }}</div>
        <div><b>Assigned To:</b> {{ visit.data.assigned_to }}</div>
        <div><b>Check-in:</b> {{ visit.data.check_in_time || '-' }}</div>
        <div><b>Check-out:</b> {{ visit.data.check_out_time || '-' }}</div>
      </div>

      <div class="flex gap-2">
        <button class="px-3 py-1 border rounded"
                @click="onCheckIn"
                :disabled="checkIn.loading || !canCheckIn">
          {{ checkIn.loading ? 'Checking in…' : 'Check-in' }}
        </button>

        <button class="px-3 py-1 border rounded"
                @click="onCheckOut"
                :disabled="checkOut.loading || !canCheckOut">
          {{ checkOut.loading ? 'Checking out…' : 'Check-out' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useVisits } from '@/composables/useVisits'

const route = useRoute()
const visitId = route.params.visitId
const { visit, loadVisit, checkIn, checkOut, canCheckIn, canCheckOut } = useVisits()

onMounted(() => loadVisit(visitId))
watch(() => route.params.visitId, (id) => id && loadVisit(id))

function onCheckIn() {
  checkIn.update({ params: { dt: 'Visit', dn: visit.data.name, method: 'check_in' } })
  checkIn.fetch()
}
function onCheckOut() {
  checkOut.update({ params: { dt: 'Visit', dn: visit.data.name, method: 'check_out' } })
  checkOut.fetch()
}
</script>
