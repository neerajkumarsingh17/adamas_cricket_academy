import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { Button } from '../../../components/Button'
import { Field, inputClass } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import type { StudentAccommodation } from '../api/student'
import { useBuildings, useUpdateAccommodation } from '../hooks/useStudents'

// Hostel/Admin only — the only roles that ever reach this dialog, since
// AccommodationCard (StudentProfilePage's academy tab) only renders the
// "Assign" button behind <Can module="residential" verb="edit">.
export function AccommodationDialog({
  studentId,
  accommodation,
  onClose,
}: {
  studentId: string
  accommodation: StudentAccommodation
  onClose: () => void
}) {
  const { data: buildings } = useBuildings()
  const updateAccommodation = useUpdateAccommodation(studentId)
  const [building, setBuilding] = useState(accommodation.building ?? '')
  const [roomNumber, setRoomNumber] = useState(accommodation.room_number)

  async function onSubmit() {
    try {
      await updateAccommodation.mutateAsync({
        building: building || null,
        room_number: roomNumber,
      })
      onClose()
    } catch {
      // Surfaced below via updateAccommodation.error
    }
  }

  return (
    <Modal title="Assign accommodation" onClose={onClose}>
      <div className="space-y-4 p-5">
        <Field label="Building">
          <select
            className={inputClass}
            value={building}
            onChange={(e) => setBuilding(e.target.value)}
          >
            <option value="">Not assigned</option>
            {buildings?.results.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Room number">
          <input
            className={inputClass}
            value={roomNumber}
            onChange={(e) => setRoomNumber(e.target.value)}
          />
        </Field>
        {updateAccommodation.isError && (
          <p className="text-sm text-red-600">
            {updateAccommodation.error instanceof ApiError
              ? updateAccommodation.error.message
              : 'Could not save this assignment.'}
          </p>
        )}
        <div className="flex justify-end gap-2 border-t border-gray-100 pt-4">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={updateAccommodation.isPending} onClick={() => void onSubmit()}>
            {updateAccommodation.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
