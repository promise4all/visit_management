import { createResource } from 'frappe-ui'
import { ref } from 'vue'

export function useWeeklySchedule() {
  // Fetch rows for current user/team – replace with your real method when available
  // current week schedule rows for logged-in user
  const rows = createResource({
    url: 'visit_management.visit_management.api.get_weekly_schedule',
    makeParams() { return {} },
    auto: false,
  })

  const approveRow = createResource({
    url: 'visit_management.visit_management.api.approve_weekly_row',
    makeParams({ name }) { return { name, create_visit: 1 } },
    onSuccess() { rows.reload() },
  })

  const createPlannedVisits = createResource({
    url: 'visit_management.visit_management.api.create_planned_visits',
    onSuccess() { rows.reload() },
  })

  function load() { rows.fetch() }

  return { rows, load, approveRow, createPlannedVisits }
}
