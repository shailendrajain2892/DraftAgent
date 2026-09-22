import { MOCK_SCENARIO, SCENARIOS, USE_MOCKS } from '../api'

/** Dev only: switch fixture scenarios without editing .env. */
export function MockScenarioBar() {
  if (!USE_MOCKS) return null

  const change = (scenario) => {
    const url = new URL(window.location.href)
    url.searchParams.set('mock', scenario)
    sessionStorage.clear()
    window.location.href = url.toString()
  }

  return (
    <div className="mock-bar">
      <span className="mock-tag">mocks</span>
      <select value={MOCK_SCENARIO} onChange={(event) => change(event.target.value)} aria-label="Mock scenario">
        {SCENARIOS.map((scenario) => (
          <option key={scenario} value={scenario}>
            {scenario}
          </option>
        ))}
      </select>
    </div>
  )
}
