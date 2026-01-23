<template>
  <Dialog v-model="show" :options="{ size: '3xl' }">
    <template #body>
      <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
              {{ visit?.data?.name || __('Visit Details') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button
              v-if="!isMobileView"
              variant="ghost"
              :tooltip="__('Open in full page')"
              icon="maximize-2"
              class="w-7"
              @click="openFullPage"
            />
            <Button
              icon="x"
              variant="ghost"
              class="w-7"
              @click="show = false"
            />
          </div>
        </div>
        <div v-if="visit?.data" class="flex flex-col gap-3.5">
          <div
            v-for="field in detailFields"
            :key="field.name"
            class="flex gap-2 text-base text-ink-gray-8"
          >
            <div class="grid size-7 place-content-center">
              <component :is="field.icon" />
            </div>
            <div class="flex min-h-7 w-full items-center gap-2">
              <div class="flex-1">
                <div class="text-sm text-ink-gray-6">{{ field.label }}</div>
                <div :class="field.color ? `text-${field.color}-600 font-medium` : 'font-medium'">
                  {{ field.value }}
                </div>
              </div>
              <div v-if="field.link">
                <ArrowUpRightIcon
                  class="h-4 w-4 shrink-0 cursor-pointer text-ink-gray-5 hover:text-ink-gray-8"
                  @click="() => field.link()"
                />
              </div>
            </div>
          </div>
        </div>
        <div v-else class="flex justify-center py-8">
          <LoadingIndicator class="h-6 w-6" />
        </div>
      </div>
      <div class="flex gap-2 px-4 pb-7 pt-4 sm:px-6">
        <Button
          v-if="canCheckIn"
          variant="solid"
          :label="__('Check-in')"
          class="flex-1"
          @click="handleCheckIn"
        />
        <Button
          v-if="canCheckOut"
          variant="solid"
          :label="__('Check-out')"
          class="flex-1"
          @click="handleCheckOut"
        />
        <Button
          variant="subtle"
          :label="__('View Full Details')"
          class="flex-1"
          @click="openFullPage"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import ContactsIcon from '@/components/Icons/ContactsIcon.vue'
import AvatarIcon from '@/components/Icons/AvatarIcon.vue'
import CheckCircleIcon from '@/components/Icons/CheckCircleIcon.vue'
import { isMobileView } from '@/composables/settings'
import { LoadingIndicator, Dialog, Button } from 'frappe-ui'
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const show = defineModel()
const visit = defineModel('visit')

const emit = defineEmits(['checkIn', 'checkOut'])

const canCheckIn = computed(() => {
  return visit.value?.data && !visit.value.data.check_in_time && visit.value.data.status !== 'Cancelled'
})

const canCheckOut = computed(() => {
  return visit.value?.data && visit.value.data.check_in_time && !visit.value.data.check_out_time && visit.value.data.status !== 'Cancelled'
})

const detailFields = computed(() => {
  if (!visit.value?.data) return []
  
  const v = visit.value.data
  return [
    {
      name: 'status',
      label: __('Status'),
      value: v.status,
      icon: CheckCircleIcon,
      color: getStatusColor(v.status),
    },
    {
      name: 'client',
      label: __('Client'),
      value: `${v.client_type}: ${v.client}`,
      icon: AvatarIcon,
      link: () => {
        const routes = {
          'CRM Lead': 'Lead',
          'CRM Deal': 'Deal',
          'CRM Organization': 'Organization',
          'Customer': null,
        }
        const route = routes[v.client_type]
        if (route) {
          router.push({ name: route, params: { [route.toLowerCase() + 'Id']: v.client } })
          show.value = false
        }
      },
    },
    {
      name: 'contact',
      label: __('Contact'),
      value: v.contact || __('Not specified'),
      icon: ContactsIcon,
    },
    {
      name: 'scheduled_time',
      label: __('Scheduled Time'),
      value: formatDateTime(v.scheduled_time),
      icon: CalendarIcon,
    },
    {
      name: 'check_in_time',
      label: __('Check-in Time'),
      value: v.check_in_time ? formatDateTime(v.check_in_time) : __('Not checked in'),
      icon: CalendarIcon,
    },
    {
      name: 'check_out_time',
      label: __('Check-out Time'),
      value: v.check_out_time ? formatDateTime(v.check_out_time) : __('Not checked out'),
      icon: CalendarIcon,
    },
  ]
})

function getStatusColor(status) {
  const colors = {
    'Planned': 'blue',
    'In Progress': 'orange',
    'Completed': 'green',
    'Cancelled': 'gray',
  }
  return colors[status] || 'gray'
}

function formatDateTime(dt) {
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleString()
  } catch {
    return dt
  }
}

function openFullPage() {
  if (visit.value?.data?.name) {
    router.push({ name: 'Visit', params: { visitId: visit.value.data.name } })
    show.value = false
  }
}

function handleCheckIn() {
  emit('checkIn', visit.value.data.name)
}

function handleCheckOut() {
  emit('checkOut', visit.value.data.name)
}
</script>
