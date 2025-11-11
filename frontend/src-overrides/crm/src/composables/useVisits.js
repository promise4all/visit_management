import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'

// Basic Visit resources (list + detail + actions). Expand fields as needed.
export function useVisits() {
  const filters = ref({})
  const pagination = ref({ start: 0, page_length: 20 })

  const list = createResource({
    url: 'frappe.client.get_list',
    params: () => ({
      doctype: 'Visit',
      fields: [
        'name','status','client_type','client','assigned_to','scheduled_time','check_in_time','check_out_time','visit_duration_minutes'
      ],
      order_by: 'modified desc',
      filters: filters.value,
      limit_start: pagination.value.start,
      limit_page_length: pagination.value.page_length,
    }),
    auto: true,
    cache: ['Visit','list', pagination.value.start],
  })

  const currentVisitName = ref(null)
  const visit = createResource({
    url: 'frappe.client.get',
    params: () => ({ doctype: 'Visit', name: currentVisitName.value }),
    auto: false,
    cache: () => currentVisitName.value && ['Visit', currentVisitName.value],
  })

  function loadVisit(name) {
    currentVisitName.value = name
    visit.fetch()
  }

  // Actions
  const checkIn = createResource({ url: 'run_doc_method', onSuccess() { visit.reload(); list.reload() } })
  const checkOut = createResource({ url: 'run_doc_method', onSuccess() { visit.reload(); list.reload() } })
  const createMaintenanceVisit = createResource({ url: 'run_doc_method', onSuccess() { visit.reload() } })

  function setFilter(key, value) {
    if (value == null || value === '') delete filters.value[key]
    else filters.value[key] = value
    list.reload()
  }

  function nextPage() {
    pagination.value.start += pagination.value.page_length
    list.reload()
  }
  function prevPage() {
    pagination.value.start = Math.max(0, pagination.value.start - pagination.value.page_length)
    list.reload()
  }

  const canCheckIn = computed(() => {
    const v = visit.data
    if (!v) return false
    return !v.check_in_time && v.status !== 'Completed' && v.status !== 'Cancelled'
  })
  const canCheckOut = computed(() => {
    const v = visit.data
    if (!v) return false
    return !!v.check_in_time && !v.check_out_time && v.status !== 'Completed' && v.status !== 'Cancelled'
  })

  return {
    list, visit, loadVisit, filters, setFilter, nextPage, prevPage,
    checkIn, checkOut, createMaintenanceVisit,
    canCheckIn, canCheckOut,
    pagination,
  }
}
