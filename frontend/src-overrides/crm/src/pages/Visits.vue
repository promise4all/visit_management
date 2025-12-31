<template>
  <div class="space-y-4">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="Visits" />
      </template>
      <template #right-header>
        <div class="flex items-end gap-2">
          <FSelect v-model="status" :options="statusOptions" class="min-w-[12rem]" />
          <Button variant="solid" :label="__('Apply')" @click="reload" />
        </div>
      </template>
    </LayoutHeader>

    <!-- Native CRM ViewControls: shows Header actions and standard filters -->
    <ViewControls
      class="mx-3 sm:mx-5"
      :doctype="'Visit'"
      :options="{ allowedViews: ['list'] }"
    />

    <div v-if="list.loading" class="text-ink-gray-5">{{ __('Loading…') }}</div>
    <div v-else>
      <template v-if="list.error">
        <div class="mx-3 sm:mx-5">
          <div class="rounded border border-destructive-6/30 bg-destructive-1 p-4 text-destructive-6">
            {{ __('Failed to load visits:') }}
            <span class="font-mono">{{ list.error.message || list.error }}</span>
          </div>
        </div>
      </template>
      <template v-else>
        <div v-if="(list.data || []).length === 0" class="mx-3 sm:mx-5">
          <div class="rounded border border-outline-2 p-6 text-center text-ink-gray-6">
            <div class="text-base font-medium mb-1">{{ __('No visits found') }}</div>
            <div class="text-sm">{{ __('Try changing filters or create a new visit.') }}</div>
          </div>
        </div>
        <ListView
          v-else
          :columns="columns"
          :rows="rows"
          :options="{
            getRowRoute: (row) => ({ name: 'Visit', params: { visitId: row.name } }),
            selectable: true,
            showTooltip: false,
            resizeColumn: false,
          }"
          row-key="name"
          v-model="list"
        >
        <template #bulkActions>
          <ListBulkActions v-model="list" doctype="Visit" :options="{ hideEdit: true, hideAssign: true }" />
        </template>
        <ListHeader class="mx-3 sm:mx-5">
          <ListHeaderItem
            v-for="column in columns"
            :key="column.key"
            :item="column"
          />
        </ListHeader>
        <ListRows class="mx-3 sm:mx-5" :rows="rows" v-slot="{ column, item }" doctype="Visit">
          <ListRowItem :item="item" :align="column.align">
            <template #prefix>
              <ArrowUpRightIcon v-if="column.key === 'name'" class="h-4 w-4 text-ink-gray-5" />
              <AvatarIcon v-else-if="column.key === 'client'" class="h-4 w-4 text-ink-gray-5" />
              <IndicatorIcon v-else-if="column.key === 'status'" :class="getStatusColor(item.columns[column.key].label)" />
            </template>
            <template #default="{ label }">
              <div class="truncate text-base">
                <Tooltip :text="label"><span>{{ label }}</span></Tooltip>
              </div>
            </template>
          </ListRowItem>
        </ListRows>
        <ListFooter
          v-if="totalCount && totalCount.data != null"
          class="border-t px-3 py-2 sm:px-5"
          v-model="pageLength"
          :options="{ rowCount: (list.data || []).length, totalCount: totalCount.data || 0 }"
          @loadMore="nextPage"
        />
        </ListView>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useVisits } from '@/composables/useVisits'
import ListRows from '@/components/ListViews/ListRows.vue'
import { Select as FSelect, ListView, ListHeader, ListHeaderItem, ListRowItem, ListFooter, Tooltip } from 'frappe-ui'
import ViewControls from '@/components/ViewControls.vue'
import AvatarIcon from '@/components/Icons/AvatarIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ListBulkActions from '@/components/ListBulkActions.vue'

const statusOptions = [
  { label: __('All'), value: '' },
  { label: __('Planned'), value: 'Planned' },
  { label: __('In Progress'), value: 'In Progress' },
  { label: __('Completed'), value: 'Completed' },
  { label: __('Cancelled'), value: 'Cancelled' },
]

const { list, totalCount, setFilter, nextPage, prevPage, pagination } = useVisits()
const status = ref('')
const pageLength = ref(20)

function reload() {
  setFilter('status', status.value || undefined)
}

watch(status, reload)

watch(pageLength, (val, old) => {
  if (val === old) return
  pagination.value.page_length = val
  pagination.value.start = 0
  list.reload();
  if (totalCount?.reload) totalCount.reload()
})

function goTo(name) {
  // Navigate to Visit detail using the named route
  window.location.href = `/crm/visits/${encodeURIComponent(name)}`
}

function getStatusColor(status) {
  const colors = {
    'Planned': 'text-blue-600',
    'In Progress': 'text-orange-600',
    'Completed': 'text-green-600',
    'Cancelled': 'text-gray-600',
  }
  return colors[status] || 'text-gray-600'
}

// ListView columns definition to align with CRM patterns
const columns = [
  { key: 'name', label: __('Visit'), align: 'left' },
  { key: 'client_type', label: __('Client Type'), align: 'left' },
  { key: 'client', label: __('Client'), align: 'left' },
  { key: 'status', label: __('Status'), align: 'left' },
  { key: 'scheduled_time', label: __('Scheduled Time'), align: 'left' },
]

// Map backend list data to ListView row+column shape
const rows = computed(() => {
  const data = list.data || []
  return data.map((v) => ({
    name: v.name,
    columns: {
      name: { label: v.name },
      client_type: { label: v.client_type },
      client: { label: v.client },
      status: { label: v.status },
      scheduled_time: { label: v.scheduled_time || '' },
    },
  }))
})
</script>
