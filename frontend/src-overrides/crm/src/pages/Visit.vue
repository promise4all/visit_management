<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="breadcrumbs" />
    </template>
    <template #right-header>
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
        <Button
          v-if="visit.data?.docstatus === 1 && visit.data?.status !== 'Cancelled'"
          variant="ghost"
          label="Cancel"
          @click="onCancel"
        />
      </div>
    </template>
  </LayoutHeader>

  <div v-if="visit.data?.name" class="h-full overflow-auto p-6 sm:p-8">
    <!-- Visit Header -->
    <div class="mb-6">
      <div class="flex items-start justify-between">
        <div>
          <div class="text-2xl font-semibold text-ink-gray-9">{{ visit.data?.name }}</div>
          <div class="mt-1 flex items-center gap-2 text-base text-ink-gray-7">
            <IndicatorIcon :class="getStatusColor(visit.data?.status)" />
            <span class="font-medium">{{ visit.data?.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Client & Contact Info -->
    <div class="mb-4 rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
      <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Client Information') }}</div>
      <div class="grid gap-4 md:grid-cols-2">
        <div v-if="visit.data?.client_type" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Client Type') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.client_type }}</span>
        </div>
        <div v-if="visit.data?.client" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Client') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.client }}</span>
        </div>
        <div v-if="visit.data?.contact" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Contact') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.contact }}</span>
        </div>
        <div v-if="visit.data?.assigned_to" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Assigned To') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.assigned_to }}</span>
        </div>
      </div>
    </div>

    <!-- Visit Details -->
    <div class="mb-4 rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
      <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Visit Details') }}</div>
      <div class="grid gap-4 md:grid-cols-2">
        <div v-if="visit.data?.subject" class="flex flex-col gap-1 md:col-span-2">
          <span class="text-xs text-ink-gray-6">{{ __('Subject') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.subject }}</span>
        </div>
        <div v-if="visit.data?.scheduled_time" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Scheduled Time') }}</span>
          <span class="text-base text-ink-gray-9">{{ formatDate(visit.data.scheduled_time) }}</span>
        </div>
        <div v-if="visit.data?.visit_duration_minutes" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Duration') }}</span>
          <span class="text-base text-ink-gray-9">{{ visit.data.visit_duration_minutes }} {{ __('minutes') }}</span>
        </div>
      </div>
    </div>

    <!-- Check-in/Check-out Times -->
    <div v-if="visit.data?.check_in_time || visit.data?.check_out_time" class="mb-4 rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
      <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Activity') }}</div>
      <div class="grid gap-4 md:grid-cols-2">
        <div v-if="visit.data?.check_in_time" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Check-in Time') }}</span>
          <span class="text-base text-ink-gray-9">{{ formatDate(visit.data.check_in_time) }}</span>
        </div>
        <div v-if="visit.data?.check_out_time" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Check-out Time') }}</span>
          <span class="text-base text-ink-gray-9">{{ formatDate(visit.data.check_out_time) }}</span>
        </div>
      </div>
    </div>

    <!-- Photos Section -->
    <div v-if="checkInPhotos.length || checkOutPhotos.length" class="mb-4">
      <div class="mb-3 text-lg font-semibold text-ink-gray-9">{{ __('Photos') }}</div>
      <div class="grid gap-4">
        <div v-if="checkInPhotos.length" class="rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
          <div class="mb-3 text-sm font-medium text-ink-gray-7">{{ __('Check-in Photos') }}</div>
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            <a
              v-for="(photo, idx) in checkInPhotos"
              :key="`checkin-${idx}`"
              :href="photo.file_url"
              target="_blank"
              class="group relative block aspect-square overflow-hidden rounded-lg border border-outline-2 shadow-sm transition-all hover:shadow-md"
            >
              <img
                :src="photo.file_url"
                :alt="`Check-in Photo ${idx + 1}`"
                class="h-full w-full object-cover transition-transform duration-200 group-hover:scale-110"
              />
              <div class="absolute inset-0 bg-black opacity-0 transition-opacity group-hover:opacity-10"></div>
            </a>
          </div>
        </div>
        <div v-if="checkOutPhotos.length" class="rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
          <div class="mb-3 text-sm font-medium text-ink-gray-7">{{ __('Check-out Photos') }}</div>
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            <a
              v-for="(photo, idx) in checkOutPhotos"
              :key="`checkout-${idx}`"
              :href="photo.file_url"
              target="_blank"
              class="group relative block aspect-square overflow-hidden rounded-lg border border-outline-2 shadow-sm transition-all hover:shadow-md"
            >
              <img
                :src="photo.file_url"
                :alt="`Check-out Photo ${idx + 1}`"
                class="h-full w-full object-cover transition-transform duration-200 group-hover:scale-110"
              />
              <div class="absolute inset-0 bg-black opacity-0 transition-opacity group-hover:opacity-10"></div>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Location Section -->
    <div v-if="locationData" class="mb-4">
      <div class="mb-3 text-lg font-semibold text-ink-gray-9">{{ __('Location') }}</div>
      <div class="rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
        <div class="mb-3 flex items-center gap-2 text-sm text-ink-gray-7">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span class="font-medium">{{ locationData.lat }}, {{ locationData.lng }}</span>
          <a :href="`https://www.google.com/maps?q=${locationData.lat},${locationData.lng}`" target="_blank" class="ml-2 text-blue-600 hover:text-blue-700">
            {{ __('Open in Google Maps') }}
          </a>
        </div>
        <div class="h-80 w-full overflow-hidden rounded-lg border border-outline-2">
          <iframe
            :src="`https://maps.google.com/maps?q=${locationData.lat},${locationData.lng}&z=15&output=embed`"
            width="100%"
            height="100%"
            style="border: 0"
            allowfullscreen
            loading="lazy"
            referrerpolicy="no-referrer-when-downgrade"
          ></iframe>
        </div>
      </div>
    </div>

    <!-- Visit Outcome Section -->
    <div v-if="visit.data?.visit_outcome" class="mb-4 rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
      <div class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Outcome') }}</div>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Visit Outcome') }}</span>
          <span class="text-base font-medium text-ink-gray-9">{{ visit.data.visit_outcome }}</span>
        </div>
        <div v-if="visit.data?.next_follow_up" class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-6">{{ __('Next Follow-up') }}</span>
          <span class="text-base text-ink-gray-9">{{ formatDate(visit.data.next_follow_up) }}</span>
        </div>
      </div>
    </div>

    <!-- Report Section -->
    <div v-if="hasReportData" class="mb-4">
      <div class="mb-3 text-lg font-semibold text-ink-gray-9">{{ __('Visit Report') }}</div>
      <div class="rounded-lg border border-outline-2 bg-white p-5 shadow-sm">
        <div class="grid gap-4">
          <div v-if="visit.data?.competitor_info" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Competitor Information') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.competitor_info }}</p>
          </div>
          <div v-if="visit.data?.existing_fleet" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Existing Fleet Information') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.existing_fleet }}</p>
          </div>
          <div v-if="visit.data?.requirements_received" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Requirements Received') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.requirements_received }}</p>
          </div>
          <div v-if="visit.data?.future_prospects" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Future Prospects') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.future_prospects }}</p>
          </div>
          <div v-if="visit.data?.product_target" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Potential Product Target') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.product_target }}</p>
          </div>
          <div v-if="visit.data?.customer_feedback" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Customer Feedback') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.customer_feedback }}</p>
          </div>
          <div v-if="visit.data?.additional_notes" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Additional Notes') }}</span>
            <p class="text-sm text-ink-gray-8">{{ visit.data.additional_notes }}</p>
          </div>
          <div v-if="visit.data?.report_attachment" class="flex flex-col gap-2">
            <span class="text-xs font-semibold text-ink-gray-6">{{ __('Report Attachment') }}</span>
            <a :href="visit.data.report_attachment" target="_blank" class="text-sm text-blue-600 hover:text-blue-700">
              {{ __('Download Report') }}
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Activity Log Section -->
    <div v-if="visit.data?.visit_logs && visit.data.visit_logs.length" class="mb-4">
      <div class="mb-3 text-lg font-semibold text-ink-gray-9">{{ __('Activity Log') }}</div>
      <div class="rounded-lg border border-outline-2 bg-white shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="border-b border-outline-2 bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold text-ink-gray-6">{{ __('Time') }}</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-ink-gray-6">{{ __('Activity') }}</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-ink-gray-6">{{ __('User') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(log, idx) in visit.data.visit_logs" :key="idx" class="border-b border-outline-2 last:border-0">
                <td class="px-4 py-3 text-sm text-ink-gray-8">{{ formatDate(log.timestamp) }}</td>
                <td class="px-4 py-3 text-sm text-ink-gray-8">{{ log.activity }}</td>
                <td class="px-4 py-3 text-sm text-ink-gray-7">{{ log.user }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="p-5 text-ink-gray-5">{{ __('Loading…') }}</div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import { Breadcrumbs, Button, Dropdown } from 'frappe-ui'
import { onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useVisits } from '@/composables/useVisits'
import { call } from 'frappe-ui'

const route = useRoute()
const visitId = route.params.visitId
const { visit, list, loadVisit, checkIn, checkOut, canCheckIn, canCheckOut } = useVisits()

const breadcrumbs = computed(() => [
  { label: __('Visits'), route: { name: 'Visits' } },
  { label: visitId },
])

function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString()
  } catch (e) {
    return value
  }
}

const excludedFields = new Set(['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx', 'check_in_photo', 'check_out_photo', 'check_in_location', 'check_out_location', '_assign', '_comments', '_liked_by'])

// Removed detailFields - now using direct field access in template

const checkInPhotos = computed(() => {
  try {
    const photoStr = visit.data?.check_in_photo
    if (!photoStr) return []
    // Photos are stored as single file URL strings, not JSON arrays
    // Convert to object with file_url property for template compatibility
    return [{ file_url: photoStr }].filter(p => p.file_url)
  } catch (e) {
    console.error('Error parsing check_in_photo:', e)
    return []
  }
})

const checkOutPhotos = computed(() => {
  try {
    const photoStr = visit.data?.check_out_photo
    if (!photoStr) return []
    // Photos are stored as single file URL strings, not JSON arrays
    // Convert to object with file_url property for template compatibility
    return [{ file_url: photoStr }].filter(p => p.file_url)
  } catch (e) {
    console.error('Error parsing check_out_photo:', e)
    return []
  }
})

const locationData = computed(() => {
  try {
    const location = visit.data?.check_in_location || visit.data?.check_out_location
    if (!location) return null
    
    // Location is stored as text: "Latitude: 6.4937898, Longitude: 3.1679257"
    // Parse this format to extract lat/lng
    if (typeof location === 'string') {
      const latMatch = location.match(/Latitude:\s*([-\d.]+)/i)
      const lngMatch = location.match(/Longitude:\s*([-\d.]+)/i)
      if (latMatch && lngMatch) {
        return {
          lat: parseFloat(latMatch[1]),
          lng: parseFloat(lngMatch[1])
        }
      }
    }
    // If already an object with lat/lng, use it
    if (location && typeof location === 'object' && location.lat && location.lng) {
      return location
    }
    return null
  } catch (e) {
    console.error('Error parsing location:', e)
    return null
  }
})

const hasReportData = computed(() => {
  const v = visit.data
  if (!v) return false
  return !!(
    v.competitor_info || 
    v.existing_fleet || 
    v.requirements_received || 
    v.future_prospects || 
    v.product_target || 
    v.customer_feedback || 
    v.additional_notes || 
    v.report_attachment
  )
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

async function capturePhoto() {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.capture = 'environment'
    input.onchange = () => {
      const file = input.files && input.files[0]
      if (!file) {
        reject(new Error('No file selected'))
        return
      }
      const reader = new FileReader()
      reader.onload = () => {
        const dataUrl = reader.result
        const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl
        const timestamp = new Date().toISOString().replace(/[:\s.]/g, '-')
        resolve({
          base64,
          filename: `photo-${timestamp}.jpg`
        })
      }
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(file)
    }
    input.click()
  })
}

function getCurrentLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        })
      },
      () => resolve(null)
    )
  })
}

async function onCheckIn() {
  if (!visit.data) return
  try {
    const photo = await capturePhoto()
    const location = await getCurrentLocation()
    await checkIn.submit({
      dt: 'Visit',
      dn: visit.data.name,
      method: 'check_in',
      args: {
        photo_data: photo.base64,
        photo_filename: photo.filename,
        location: location ? JSON.stringify(location) : null
      }
    })
    visit.reload()
  } catch (err) {
    console.error('Check-in failed:', err)
  }
}

async function onCheckOut() {
  if (!visit.data) return
  try {
    const photo = await capturePhoto()
    const location = await getCurrentLocation()
    await checkOut.submit({
      dt: 'Visit',
      dn: visit.data.name,
      method: 'check_out',
      args: {
        photo_data: photo.base64,
        photo_filename: photo.filename,
        location: location ? JSON.stringify(location) : null
      }
    })
    visit.reload()
  } catch (err) {
    console.error('Check-out failed:', err)
  }
}

async function onCancel() {
  if (!visit.data) return
  if (!confirm(__('Are you sure you want to cancel this visit?'))) return
  try {
    await call('frappe.desk.form.save.cancel', {
      doctype: 'Visit',
      name: visit.data.name
    })
    visit.reload()
    list.reload()
  } catch (err) {
    console.error('Cancel failed:', err)
  }
}
</script>
