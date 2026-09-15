import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('shows the public landing page at /', async () => {
    render(<App />)
    expect(
      await screen.findByRole('link', { name: /sign in to your dashboard/i }),
    ).toBeTruthy()
  })
})
