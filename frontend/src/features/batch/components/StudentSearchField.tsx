import { useEffect, useState } from 'react'
import { inputClass } from '../../../components/Field'
import type { Student } from '../api/batch'
import { batchApi } from '../api/batch'

// Same debounced pick-from-dropdown shape as
// features/payment/components/PersonSearchField.tsx, over students
// (code or name) instead of persons (name or mobile).
export function StudentSearchField({
  selected,
  onSelect,
}: {
  selected: Student | null
  onSelect: (student: Student | null) => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Student[]>([])
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      setIsOpen(false)
      return
    }
    const timeout = setTimeout(() => {
      void batchApi
        .lookupStudents(query)
        .then((students) => {
          setResults(students)
          setIsOpen(true)
        })
        .catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(timeout)
  }, [query])

  if (selected) {
    return (
      <div className="flex min-h-[44px] items-center justify-between rounded-md border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm">
        <span className="text-gray-900">
          {selected.person.first_name} {selected.person.last_name}{' '}
          <span className="font-mono text-xs text-gray-500">{selected.student_code}</span>
        </span>
        <button
          type="button"
          className="text-xs font-medium text-brand-600 hover:underline"
          onClick={() => onSelect(null)}
        >
          Change
        </button>
      </div>
    )
  }

  return (
    <div className="relative">
      <input
        className={inputClass}
        placeholder="Search by student code or name…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setIsOpen(true)}
      />
      {isOpen && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-gray-400">No matches.</li>
          ) : (
            results.map((student) => (
              <li key={student.id}>
                <button
                  type="button"
                  className="block min-h-[44px] w-full px-3 py-2 text-left text-sm hover:bg-brand-50"
                  onClick={() => {
                    onSelect(student)
                    setQuery('')
                    setIsOpen(false)
                  }}
                >
                  {student.person.first_name} {student.person.last_name}{' '}
                  <span className="font-mono text-xs text-gray-500">{student.student_code}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
