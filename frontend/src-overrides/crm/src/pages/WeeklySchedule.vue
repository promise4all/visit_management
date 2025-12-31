<template>
  <div class="space-y-4">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="WeeklySchedule" />
      </template>
      <template #right-header>
        <div class="flex gap-2">
          <Button
            variant="subtle"
            :label="rows.loading ? __('Loading…') : __('Reload')"
            :disabled="rows.loading"
            @click="load"
          />
          <Button
            variant="solid"
            :label="createPlannedVisits.loading ? __('Creating…') : __('Create Planned Visits')"
            :disabled="createPlannedVisits.loading"
            @click="createVisits"
          />
        </div>
      </template>
    </LayoutHeader>

    <div>
      <div v-if="rows.loading" class="text-ink-gray-5">{{ __('Loading schedule…') }}</div>
      <div v-else>
        <div v-if="rows.error" class="mx-3 sm:mx-5">
          <div class="rounded border border-destructive-6/30 bg-destructive-1 p-4 text-destructive-6">
            {{ __('Failed to load schedule:') }}
            <span class="font-mono">{{ rows.error.message || rows.error }}</span>
          </div>
        </div>
        <div v-else-if="(rows.data || []).length === 0" class="mx-3 sm:mx-5">
          <div class="rounded border border-outline-2 p-6 text-center text-ink-gray-6">
            <div class="text-base font-medium mb-1">{{ __('No weekly schedule found for this week.') }}</div>
            <div class="text-sm">{{ __('Try reloading or creating planned visits.') }}</div>
          </div>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="r in rows.data || []"
            :key="r.name"
            class="rounded border border-outline-2 p-3 flex justify-between items-center"
          >
            <div class="text-sm space-y-0.5">
              <div class="font-medium">{{ r.client }} • {{ r.purpose }}</div>
              <div class="text-ink-gray-5">{{ r.day }} {{ r.time_slot }}</div>
              <div class="text-ink-gray-4" v-if="r.status">{{ __('Status') }}: {{ r.status }}</div>
            </div>
            <Button
              v-if="r.docstatus !== 1 && r.status !== 'Approved'"
              size="sm"
              variant="subtle"
              :label="approveRow.loading ? __('Approving…') : __('Approve')"
              :disabled="approveRow.loading"
              @click="approve(r.name)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
  
</template>

<script setup>
import { onMounted } from 'vue'
import { useWeeklySchedule } from '@/composables/useWeeklySchedule'
const { rows, load, approveRow, createPlannedVisits } = useWeeklySchedule()

onMounted(() => {
  // Auto-load current week's schedule on mount
  load()
})

function approve(name) {
  approveRow.update({ params: { name } }); approveRow.fetch()
}
function createVisits() {
  createPlannedVisits.fetch()
}
</script>
