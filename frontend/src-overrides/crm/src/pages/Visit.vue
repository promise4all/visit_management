<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="breadcrumbs" />
    </template>
    <template #right-header>
      <AssignTo v-model="assignees" doctype="Visit" :docname="visitId" />
      <Dropdown
        v-if="visit.data && statusOptions.length"
        :options="statusOptions"
        placement="right"
      >
        <template #default="{ open }">
          <Button
            v-if="visit.data.status"
            :label="visit.data.status"
            :iconRight="open ? 'chevron-up' : 'chevron-down'"
          >
            <template #prefix>
              <IndicatorIcon :class="getStatusColor(visit.data.status)" />
            </template>
          </Button>
        </template>
      </Dropdown>
      <div class="flex gap-2">
        <Button
          variant="solid"
          :label="checkIn.loading ? __('Checking in…') : __('Check-in')"
          :disabled="checkIn.loading || !canCheckIn"
          @click="onCheckIn"
        />
        <Button
          variant="subtle"
          :label="checkOut.loading ? __('Checking out…') : __('Check-out')"
          :disabled="checkOut.loading || !canCheckOut"
          @click="onCheckOut"
        />
      </div>
    </template>
  </LayoutHeader>

  <div v-if="visit.data?.name" class="flex h-full overflow-hidden">
    <Tabs as="div" v-model="tabIndex" :tabs="tabs">
      <template #tab-panel>
        <Activities
          doctype="Visit"
          :docname="visitId"
          :tabs="tabs"
          v-model:tabIndex="tabIndex"
        />
      </template>
    </Tabs>
    <Resizer side="right" class="flex flex-col justify-between border-l">
      <div
        class="flex h-10.5 items-center border-b px-5 py-2.5 text-lg font-medium text-ink-gray-9"
      >
        {{ __(visitId) }}
      </div>
      <div class="flex items-center justify-start gap-5 border-b p-5">
        <Tooltip :text="__('Client')">
          <div class="group relative size-12">
            <Avatar size="3xl" class="size-12" :label="visit.data?.client" />
          </div>
        </Tooltip>
        <div class="flex flex-col gap-2.5 truncate text-ink-gray-9">
          <div class="truncate text-2xl font-medium">
            {{ visit.data?.client || __('Visit') }}
          </div>
          <div class="flex gap-1.5">
            <Button
              :tooltip="__('Attach a file')"
              :icon="AttachmentIcon"
              @click="showFilesUploader = true"
            />
          </div>
        </div>
      </div>
      <div class="flex flex-1 flex-col gap-3 overflow-auto p-5 text-base text-ink-gray-8">
        <div class="flex items-center gap-2">
          <b>{{ __('Status') }}:</b>
          <span class="flex items-center gap-1">
            <IndicatorIcon :class="getStatusColor(visit.data?.status)" />
            {{ visit.data?.status }}
          </span>
        </div>
        <div><b>{{ __('Client Type') }}:</b> {{ visit.data?.client_type }}</div>
        <div><b>{{ __('Client') }}:</b> {{ visit.data?.client }}</div>
        <div v-if="visit.data?.contact"><b>{{ __('Contact') }}:</b> {{ visit.data?.contact }}</div>
        <div><b>{{ __('Assigned To') }}:</b> {{ visit.data?.assigned_to }}</div>
        <div><b>{{ __('Subject') }}:</b> {{ visit.data?.subject || '-' }}</div>
        <div><b>{{ __('Scheduled Time') }}:</b> {{ visit.data?.scheduled_time || '-' }}</div>
        <div><b>{{ __('Check-in') }}:</b> {{ visit.data?.check_in_time || '-' }}</div>
        <div><b>{{ __('Check-out') }}:</b> {{ visit.data?.check_out_time || '-' }}</div>
        <div v-if="visit.data?.visit_duration_minutes"><b>{{ __('Duration') }}:</b> {{ visit.data?.visit_duration_minutes }} {{ __('minutes') }}</div>
      </div>
    </Resizer>
  </div>
  <div v-else class="p-5 text-ink-gray-5">{{ __('Loading…') }}</div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import Activities from '@/components/Activities/Activities.vue'
import Resizer from '@/components/Resizer.vue'
import AssignTo from '@/components/AssignTo.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ActivityIcon from '@/components/Icons/ActivityIcon.vue'
import EmailIcon from '@/components/Icons/EmailIcon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import AttachmentIcon from '@/components/Icons/AttachmentIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import { Breadcrumbs, Tooltip, Avatar, Tabs, Button, Dropdown, createResource } from 'frappe-ui'
import { whatsappEnabled } from '@/composables/settings'
import { onMounted, watch, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useVisits } from '@/composables/useVisits'

const route = useRoute()
const visitId = route.params.visitId
const { visit, loadVisit, checkIn, checkOut, canCheckIn, canCheckOut } = useVisits()

const tabIndex = ref(0)
const tabs = computed(() => {
  let tabOptions = [
    {
      name: 'Activity',
      label: __('Activity'),
      icon: ActivityIcon,
    },
    {
      name: 'Emails',
      label: __('Emails'),
      icon: EmailIcon,
    },
    {
      name: 'Comments',
      label: __('Comments'),
      icon: CommentIcon,
    },
    {
      name: 'Calls',
      label: __('Calls'),
      icon: PhoneIcon,
    },
    {
      name: 'Tasks',
      label: __('Tasks'),
      icon: TaskIcon,
    },
    {
      name: 'Notes',
      label: __('Notes'),
      icon: NoteIcon,
    },
    {
      name: 'Attachments',
      label: __('Attachments'),
      icon: AttachmentIcon,
    },
    {
      name: 'WhatsApp',
      label: __('WhatsApp'),
      icon: WhatsAppIcon,
      condition: () => whatsappEnabled.value,
    },
  ]
  return tabOptions.filter((tab) => (tab.condition ? tab.condition() : true))
})

const breadcrumbs = computed(() => [
  { label: __('Visits'), route: { name: 'Visits' } },
  { label: visitId },
])

const showFilesUploader = ref(false)

const assignees = createResource({
  url: 'frappe.desk.form.assign_to.get',
  params: { doctype: 'Visit', name: visitId },
  cache: ['visit_assignees', visitId],
  auto: true,
})

const statusOptions = computed(() => [
  { label: __('Planned'), onClick: () => updateStatus('Planned') },
  { label: __('In Progress'), onClick: () => updateStatus('In Progress') },
  { label: __('Completed'), onClick: () => updateStatus('Completed') },
  { label: __('Cancelled'), onClick: () => updateStatus('Cancelled') },
])

function getStatusColor(status) {
  const colors = {
    'Planned': 'text-blue-600',
    'In Progress': 'text-orange-600',
    'Completed': 'text-green-600',
    'Cancelled': 'text-gray-600',
  }
  return colors[status] || 'text-gray-600'
}

function updateStatus(newStatus) {
  if (!visit.data) return
  visit.data.status = newStatus
  visit.reload()
}

onMounted(() => loadVisit(visitId))
watch(() => route.params.visitId, (id) => id && loadVisit(id))

function onCheckIn() {
  if (!visit.data) return
  checkIn.update({ params: { dt: 'Visit', dn: visit.data.name, method: 'check_in' } })
  checkIn.fetch()
}
function onCheckOut() {
  if (!visit.data) return
  checkOut.update({ params: { dt: 'Visit', dn: visit.data.name, method: 'check_out' } })
  checkOut.fetch()
}
</script>
