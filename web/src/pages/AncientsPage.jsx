import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

const DEFAULT_FORM = {
  strategy: 'A', summonCount: 1, startLevel: 100,
  preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
}

export default function AncientsPage() {
  const [collectors, setCollectors] = useState(null)
  const [levelHp, setLevelHp] = useState({})
  const [loadError, setLoadError] = useState('')
  const [formByCollector, setFormByCollector] = useState({})
  const [resultByCollector, setResultByCollector] = useState({})
  const [fuzzyThreshold, setFuzzyThreshold] = useState(0.75)
  const [pendingMappings, setPendingMappings] = useState({})
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.ancients
  const locale = lang === 'ru' ? 'ru-RU' : 'en-US'
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Древний' : 'Total Hunter — Ancient',
    description: lang === 'ru' ? 'Калькулятор нормы урона по Древним.' : 'Ancient damage quota calculator.',
  })

  function fmtNum(n, maxFractionDigits = 1) {
    if (n === null || n === undefined) return '—'
    return Number(n).toLocaleString(locale, { maximumFractionDigits: maxFractionDigits })
  }

  function fmtDate(iso) {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString(locale, { dateStyle: 'medium', timeStyle: 'short' })
  }

  async function refresh(threshold = fuzzyThreshold) {
    try {
      const data = await api.dashboardAncients(threshold)
      setCollectors(data.collectors)
      setLevelHp(data.ancient_level_hp || {})
      const nextForm = {}
      for (const c of data.collectors) {
        nextForm[c.slug] = { ...DEFAULT_FORM }
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

  function levelsFor(form) {
    return Array.from({ length: form.summonCount }, (_, i) => form.startLevel + i)
  }

  async function handleTroopLevelChange(slug, playerName, troopLevel) {
    await api.dashboardAncientsTroopLevel(slug, playerName, troopLevel || null)
    refresh()
  }

  async function handleCalculate(slug) {
    const form = formByCollector[slug]
    const payload = {
      strategy: form.strategy,
      summon_levels: levelsFor(form),
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
        const form = formByCollector[c.slug] || DEFAULT_FORM
        const result = resultByCollector[c.slug]
        const levels = levelsFor(form)
        const maxStartLevel = 250 - (form.summonCount - 1)

        return (
          <div key={c.slug} style={{ marginBottom: 32 }}>
            <div style={{ marginBottom: 12, fontWeight: 600 }}>{c.kingdom} / {c.clan}</div>

            {/* ── Калькулятор — наверху ── */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.calcTitle}</div>

              <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                  {cx.summonsLabel}
                  <select
                    className="input-dark"
                    value={form.summonCount}
                    onChange={e => updateForm(c.slug, { summonCount: Number(e.target.value) })}
                  >
                    {[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12 }}>
                  {cx.startLevelLabel}
                  <input
                    className="input-dark"
                    type="number" min={81} max={maxStartLevel}
                    value={form.startLevel}
                    onChange={e => updateForm(c.slug, {
                      startLevel: Math.min(Number(e.target.value), maxStartLevel),
                    })}
                  />
                </label>
              </div>

              <div style={{ marginBottom: 12 }}>
                <div className="text-muted" style={{ fontSize: 12, marginBottom: 4 }}>
                  {cx.levelsPreviewLabel}
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {levels.map(level => (
                    <span
                      key={level}
                      style={{
                        display: 'inline-flex', alignItems: 'baseline', gap: 4,
                        padding: '4px 10px', borderRadius: 8,
                        background: 'var(--elevated)', border: '1px solid var(--outline)',
                      }}
                    >
                      <span style={{ color: 'var(--on-surface)', fontWeight: 600 }}>{level}</span>
                      <span style={{ color: 'var(--credits-gold)', fontSize: 12 }}>
                        {levelHp[level] !== undefined ? `${fmtNum(levelHp[level])} ${cx.powerUnit}` : '—'}
                      </span>
                    </span>
                  ))}
                </div>
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
                <div>{cx.totalQuota}: <strong>{fmtNum(result.total_quota_millions)}</strong></div>
                {result.result.officer_quota !== undefined ? (
                  <>
                    <div>{cx.officerQuota}: {fmtNum(result.result.officer_quota, 2)}</div>
                    <div>{cx.veteranQuota}: {fmtNum(result.result.veteran_quota, 2)}</div>
                  </>
                ) : (
                  <table className="chest-table">
                    <thead>
                      <tr><th>{cx.player}</th><th>{cx.troopLevel}</th><th>{cx.totalQuota}</th></tr>
                    </thead>
                    <tbody>
                      {result.result.players.map(p => (
                        <tr key={p.name}>
                          <td>{p.name}</td><td>{p.troop_level}</td><td>{fmtNum(p.quota, 2)}</td>
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

            {/* ── История расчётов ── */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.historyTitle}</div>
              {c.history.length === 0 ? (
                <div className="text-muted">{cx.noHistory}</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {c.history.map(h => (
                    <div
                      key={h.id}
                      style={{
                        paddingLeft: 12, borderLeft: '3px solid var(--accent)',
                        display: 'flex', flexDirection: 'column', gap: 2,
                      }}
                    >
                      <div style={{ color: 'var(--on-surface2)', fontSize: 12 }}>
                        {fmtDate(h.computed_at)} · {h.strategy === 'A' ? cx.strategyAName : cx.strategyBName}
                      </div>
                      <div style={{ color: 'var(--on-surface)', fontSize: 13 }}>
                        {cx.historyLevels}: {(h.summon_levels || []).join(', ')}
                      </div>
                      <div style={{ color: 'var(--credits-gold)', fontWeight: 600 }}>
                        {cx.historyTotal}: {fmtNum(h.total_quota_millions)} {cx.powerUnit}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ── Ростер клана — внизу ── */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <label style={{ fontSize: 13, color: '#a6adc8', whiteSpace: 'nowrap' }}>
                  Точность совпадения: {Math.round(fuzzyThreshold * 100)}% — чем выше, тем строже подбор
                </label>
                <input
                  type="range" min={50} max={100} step={5}
                  value={Math.round(fuzzyThreshold * 100)}
                  onChange={e => {
                    const val = parseInt(e.target.value) / 100
                    setFuzzyThreshold(val)
                    refresh(val)
                  }}
                  style={{ width: 140 }}
                />
              </div>
              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>
              {c.roster.length === 0 ? (
                <div className="text-muted">{cx.noRoster}</div>
              ) : (
                <>
                <table className="chest-table">
                  <thead>
                    <tr>
                      <th>{cx.player}</th><th>Правильное имя</th><th>{cx.place}</th><th>{cx.points}</th><th>{cx.troopLevel}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.roster.map(p => (
                      <tr key={p.player_name}>
                        <td>{p.player_name}</td>
                        <td>
                          {p.mapping_confirmed ? (
                            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{ color: '#a6e3a1', fontWeight: 600 }}>
                                {p.mapped_name}
                              </span>
                              <button
                                style={{ fontSize: 11, padding: '1px 6px', cursor: 'pointer',
                                         background: 'transparent', border: '1px solid #6c7086',
                                         color: '#6c7086', borderRadius: 4 }}
                                onClick={async () => {
                                  await api.dashboardAncientsNameMappingDelete(c.slug, p.player_name)
                                  refresh()
                                }}
                              >
                                🔓
                              </button>
                            </span>
                          ) : (
                            <select
                              className="input-dark"
                              value={(pendingMappings[c.slug] || {})[p.player_name] ??
                                     (p.suggested_name || '')}
                              onChange={e => setPendingMappings(prev => ({
                                ...prev,
                                [c.slug]: { ...(prev[c.slug] || {}),
                                            [p.player_name]: e.target.value },
                              }))}
                              style={{ minWidth: 130 }}
                            >
                              <option value="">— не сопоставлять —</option>
                              {(c.canonical_names || []).map(name => (
                                <option key={name} value={name}>{name}</option>
                              ))}
                            </select>
                          )}
                        </td>
                        <td>{p.place ?? '—'}</td>
                        <td>{p.points !== null && p.points !== undefined ? fmtNum(p.points, 0) : '—'}</td>
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
                {Object.keys(pendingMappings[c.slug] || {}).length > 0 && (
                  <button
                    className="btn-primary"
                    style={{ marginTop: 10 }}
                    onClick={async () => {
                      const pending = pendingMappings[c.slug] || {}
                      const mappings = Object.entries(pending)
                        .filter(([, canonical]) => canonical)
                        .map(([raw_ocr_name, canonical_name]) => ({
                          raw_ocr_name, canonical_name, confirmed: true,
                        }))
                      if (mappings.length === 0) return
                      await api.dashboardAncientsNameMappings(c.slug, mappings)
                      setPendingMappings(prev => ({ ...prev, [c.slug]: {} }))
                      refresh()
                    }}
                  >
                    Сохранить маппинги
                  </button>
                )}
                </>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
