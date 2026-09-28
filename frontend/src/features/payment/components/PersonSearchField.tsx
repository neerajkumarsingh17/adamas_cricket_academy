import { useEffect, useState } from 'react'
import { inputClass } from '../../../components/Field'
import type { Person } from '../api/payment'
import { paymentApi } from '../api/payment'

// Debounced search-as-you-type, modelled on the duplicate-check pattern in
// features/enquiry/pages/EnquiryFormPage.tsx — but here the result is
// something the user picks (a person to record a payment against), not
// just a warning banner, so it renders a clickable dropdown instead.
export function PersonSearchField({
  selected,
  onSelect,
}: {
  selected: Person | null
  onSelect: (person: Person | null) => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Person[]>([])
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (query.length < 3) {
      setResults([])
      setIsOpen(false)
      return
    }
    const timeout = setTimeout(() => {
      void paymentApi
        .searchPersons(query)
        .then((people) => {
          setResults(people)
          setIsOpen(true)
        })
        .catch(() => setResults([]))
    }, 300)
    return () => clearTimeout(timeout)
  }, [query])

  if (selected) {
    return (
      <div className="flex items-center justify-between rounded-md border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm">
        <span className="text-gray-900">
          {selected.first_name} {selected.last_name} · {selected.mobile}
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
        placeholder="Search by name or mobile number…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setIsOpen(true)}
      />
      {isOpen && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-gray-400">No matches.</li>
          ) : (
            results.map((person) => (
              <li key={person.id}>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-brand-50"
                  onClick={() => {
                    onSelect(person)
                    setQuery('')
                    setIsOpen(false)
                  }}
                >
                  {person.first_name} {person.last_name} · {person.mobile}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
