import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function AncientsPage() {
  const [collectors, setCollectors] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [formByCollector, setFormByCollector] = useState({})
  const [resultByCollector, setResultByCollector] = useState({})
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.ancients
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Древний' : 'Total Hunter — Ancient',
    description: lang === 'ru' ? 'Калькулятор нормы урона по Древним.' : 'Ancient damage quota calculator.',
  })

  async function refresh() {
    try {
      const data = await api.dashboardAncients()
      setCollectors(data.collectors)
      const nextForm = {}
      for (const c of data.collectors) {
        nextForm[c.slug] = {
          strategy: 'A', summonCount: 1, levels: [100],
          preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
        }
      }
      setFormByCollector(prev => ({ ...nextForm, ...prev }))
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => { refresh() }, [])

  function updateForm(slug, patch) {
    setFormByCollector(prev => ({ ...prev, [slug]: { ...prev[slug], ...patch } }))
  }

  function updateSummonCount(slug, count) {
    const form = formByCollector[slug]
    const levels = Array.from({ length: count }, (_, i) => form.levels[i] || 100)
    updateForm(slug, { summonCount: count, levels })
  }

  function updateLevel(slug, index, value) {
    const form = formByCollector[slug]
    const levels = [...form.levels]
    levels[index] = Number(value)
    updateForm(slug, { levels })
  }

  async function handleTroopLevelChange(slug, playerName, troopLevel) {
    await api.dashboardAncientsTroopLevel(slug, playerName, troopLevel || null)
    refresh()
  }

  async function handleCalculate(slug) {
    const form = formByCollector[slug]
    const payload = {
      strategy: form.strategy,
      summon_levels: form.levels,
      amplification_coef: Number(form.amplification),
      clan_preset: form.strategy === 'B' ? form.preset : null,
      officer_count: form.strategy === 'A' ? Number(form.officerCount) : null,
      veteran_count: form.strategy === 'A' ? Number(form.veteranCount) : null,
    }
    const result = await api.dashboardAncientsCalculate(slug, payload)
    setResultByCollector(prev => ({ ...prev, [slug]: result }))
    refresh()
  }

  if (loadError) return <div className="page-content text-muted">{loadError}</div>
  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{cx.title}</h2>

      {collectors.length === 0 && <div className="text-muted" style={{ marginTop: 12 }}>{cx.noRoster}</div>}

      {collectors.map(c => {
        const form = formByCollector[c.slug] || {
          strategy: 'A', summonCount: 1, levels: [100],
          preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
        }
        const result = resultByCollector[c.slug]
        return (
          <div className="card" key={c.slug} style={{ marginBottom: 24 }}>
            <div style={{ marginBottom: 12, fontWeight: 600 }}>{c.kingdom} / {c.clan}</div>

            <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>
            {c.roster.length === 0 ? (
              <div className="text-muted" style={{ marginBottom: 16 }}>{cx.noRoster}</div>
            ) : (
              <table className="chest-table" style={{ marginBottom: 16 }}>
                <thead>
                  <tr>
                    <th>{cx.player}</th><th>{cx.place}</th><th>{cx.points}</th><th>{cx.troopLevel}</th>
                  </tr>
                </thead>
                <tbody>
                  {c.roster.map(p => (
                    <tr key={p.player_name}>
                      <td>{p.player_name}</td>
                      <td>{p.place ?? '—'}</td>
                      <td>{p.points ?? '—'}</td>
                      <td>
                        <select
                          className="input-dark"
                          value={p.troop_level || ''}
                          onChange={e => handleTroopLevelChange(c.slug, p.player_name, e.target.value)}
                        >
                          <option value="">{cx.noTroopLevel}</option>
                          {c.troop_steps.map(step => <option key={step} value={step}>{step}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.calcTitle}</div>

              <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                {cx.summonsLabel}
                <select
                  className="input-dark"
                  style={{ width: 'auto' }}
                  value={form.summonCount}
                  onChange={e => updateSummonCount(c.slug, Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>

              <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                {form.levels.map((level, i) => (
                  <label key={i} style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                    {cx.levelLabel(i + 1)}
                    <input
                      className="input-dark"
                      type="number" min={81} max={250}
                      value={level}
                      onChange={e => updateLevel(c.slug, i, e.target.value)}
                    />
                  </label>
                ))}
              </div>

              <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                  {cx.amplificationLabel}
                  <input
                    className="input-dark"
                    type="number" step="0.01"
                    value={form.amplification}
                    onChange={e => updateForm(c.slug, { amplification: e.target.value })}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                  {cx.strategyLabel}
                  <select
                    className="input-dark"
                    value={form.strategy}
                    onChange={e => updateForm(c.slug, { strategy: e.target.value })}
                  >
                    <option value="A">{cx.strategyA}</option>
                    <option value="B">{cx.strategyB}</option>
                  </select>
                </label>
              </div>

              {form.strategy === 'A' ? (
                <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                    {cx.officerCount}
                    <input
                      className="input-dark"
                      type="number" min={0}
                      value={form.officerCount}
                      onChange={e => updateForm(c.slug, { officerCount: e.target.value })}
                    />
                  </label>
                  <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                    {cx.veteranCount}
                    <input
                      className="input-dark"
                      type="number" min={0}
                      value={form.veteranCount}
                      onChange={e => updateForm(c.slug, { veteranCount: e.target.value })}
                    />
                  </label>
                </div>
              ) : (
                <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                    {cx.presetLabel}
                    <select
                      className="input-dark"
                      value={form.preset}
                      onChange={e => updateForm(c.slug, { preset: e.target.value })}
                    >
                      {c.presets.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </label>
                </div>
              )}

              <button className="btn-primary" onClick={() => handleCalculate(c.slug)}>
                {cx.calculateButton}
              </button>
            </div>

            {result && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div>{cx.totalQuota}: {result.total_quota_millions.toFixed(1)}</div>
                {result.result.officer_quota !== undefined ? (
                  <>
                    <div>{cx.officerQuota}: {result.result.officer_quota.toFixed(2)}</div>
                    <div>{cx.veteranQuota}: {result.result.veteran_quota.toFixed(2)}</div>
                  </>
                ) : (
                  <table className="chest-table">
                    <thead>
                      <tr><th>{cx.player}</th><th>{cx.troopLevel}</th><th>{cx.totalQuota}</th></tr>
                    </thead>
                    <tbody>
                      {result.result.players.map(p => (
                        <tr key={p.name}>
                          <td>{p.name}</td><td>{p.troop_level}</td><td>{p.quota.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {result.result.excluded && result.result.excluded.length > 0 && (
                  <div className="text-muted" style={{ marginTop: 8 }}>
                    {cx.excludedNote}: {result.result.excluded.join(', ')}
                  </div>
                )}
              </div>
            )}

            <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.historyTitle}</div>
            {c.history.length === 0 ? (
              <div className="text-muted">—</div>
            ) : (
              <ul>
                {c.history.map(h => (
                  <li key={h.id}>{h.computed_at} — {h.strategy} — {h.total_quota_millions.toFixed(1)}</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
