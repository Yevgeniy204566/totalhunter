import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'
import { rowShortfallClass } from '../lib/ancientQuota.js'

const DEFAULT_FORM = {
  strategy: 'A', summonCount: 1, startLevel: 100,
  preset: 'T8', amplification: 1.0, officerCount: 0, veteranCount: 0,
}

const TIERS = ['5', '6', '7', '8', '9']
const RANKS = ['', 'Глава', 'Старший', 'Офицер', 'Ветеран', 'Рядовой']

function parseTroop(troop_level) {
  if (!troop_level) return { g: '', s: '', m: '' }
  const mat = troop_level.match(/G(\d+) S(\d+) M(\d+)/)
  return mat ? { g: mat[1], s: mat[2], m: mat[3] } : { g: '', s: '', m: '' }
}

function lcsLength(a, b) {
  const m = a.length, n = b.length
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i - 1] === b[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1])
  return dp[m][n]
}

function clientFuzzyMatch(raw, candidates, cutoff) {
  if (!raw || !candidates || candidates.length === 0) return null
  const a = raw.toLowerCase()
  let best = null, bestScore = cutoff - 0.001
  for (const cand of candidates) {
    const b = cand.toLowerCase()
    if (!b) continue
    const common = lcsLength(a, b)
    const score = 2.0 * common / (a.length + b.length)
    if (score > bestScore) { bestScore = score; best = cand }
  }
  return best
}

export default function AncientsPage() {
  const [collectors, setCollectors] = useState(null)
  const [levelHp, setLevelHp] = useState({})
  const [loadError, setLoadError] = useState('')
  const [formByCollector, setFormByCollector] = useState({})
  const [resultByCollector, setResultByCollector] = useState({})
  const [fuzzyThreshold, setFuzzyThreshold] = useState(0.75)
  const [pendingMappings, setPendingMappings] = useState({})
  const [sortByCollector, setSortByCollector] = useState({})
  const [canonicalSources, setCanonicalSources] = useState([])
  const [canonicalSourceSlug, setCanonicalSourceSlug] = useState({})
  const [joinMessage, setJoinMessage] = useState('')
  const [inviteMsg, setInviteMsg] = useState({})
  const [hiddenCollectors, setHiddenCollectors] = useState([])
  const [confirmHideByCollector, setConfirmHideByCollector] = useState({})
  const [troopEdits, setTroopEdits] = useState({})
  const [manualForm, setManualForm] = useState({})
  const [manualSimilar, setManualSimilar] = useState({})
  const [confirmDeleteRoster, setConfirmDeleteRoster] = useState({})
  const [confirmClearOcr, setConfirmClearOcr] = useState({})
  const [mappingEditOpen, setMappingEditOpen] = useState({})
  const [clearOcrMsg, setClearOcrMsg] = useState({})
  const [populateMsg, setPopulateMsg] = useState({})
  const [confirmPopulate, setConfirmPopulate] = useState({})
  const [activeTab, setActiveTab] = useState('clans')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({ kingdom: '', clan: '' })
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)
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

  async function refresh(threshold) {
    const t = threshold !== undefined ? threshold : fuzzyThreshold
    try {
      const data = await api.dashboardAncients(t)
      setCollectors(data.collectors || [])
      setCanonicalSources(data.canonical_sources || [])
      setLevelHp(data.ancient_level_hp || {})
      setHiddenCollectors(data.hidden_collectors || [])
      setFormByCollector(prev => {
        const next = {}
        for (const c of (data.collectors || [])) {
          next[c.slug] = prev[c.slug] || { ...DEFAULT_FORM }
        }
        return next
      })
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const joinCode = params.get('join')
    if (joinCode) {
      params.delete('join')
      window.history.replaceState({}, '', window.location.pathname + (params.toString() ? '?' + params : ''))
      api.dashboardAncientsJoin(joinCode)
        .then(() => { setJoinMessage(cx.joinSuccess); refresh() })
        .catch(() => setJoinMessage(cx.joinError))
    }
    refresh()
  }, [])

  function updateForm(slug, patch) {
    setFormByCollector(prev => ({ ...prev, [slug]: { ...prev[slug], ...patch } }))
  }

  function toggleSort(slug, field) {
    setSortByCollector(prev => {
      const cur = prev[slug] || { field: 'place', dir: 'asc' }
      const dir = cur.field === field && cur.dir === 'asc' ? 'desc' : 'asc'
      return { ...prev, [slug]: { field, dir } }
    })
  }

  function levelsFor(form) {
    return Array.from({ length: form.summonCount }, (_, i) => form.startLevel + i)
  }

  async function handleInvite(slug) {
    try {
      const { code } = await api.dashboardAncientsInvite(slug)
      const url = `${window.location.origin}/dashboard/ancients?join=${code}`
      await navigator.clipboard.writeText(url)
      setInviteMsg(prev => ({ ...prev, [slug]: cx.inviteCopied }))
      setTimeout(() => setInviteMsg(prev => ({ ...prev, [slug]: '' })), 3000)
    } catch {
      setInviteMsg(prev => ({ ...prev, [slug]: '—' }))
    }
  }

  async function handleSetHidden(slug, hidden) {
    await api.dashboardAncientsSetHidden(slug, hidden)
    setConfirmHideByCollector(prev => ({ ...prev, [slug]: false }))
    refresh()
  }

  async function handleTroopLevelChange(slug, playerName, troopLevel) {
    try {
      await api.dashboardAncientsTroopLevel(slug, playerName, troopLevel || null)
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }

  async function handleRankChange(slug, playerName, rank) {
    try {
      await api.dashboardAncientsRank(slug, playerName, rank || null)
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }

  async function handleThresholdChange(slug, thresholds, field, value) {
    const next = { ...thresholds, [field]: parseFloat(value) || 0 }
    try {
      await api.dashboardAncientsQuotaThresholds(
        slug, next.light_pct, next.medium_pct, next.critical_pct)
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }

  function handleTroopFieldChange(slug, playerName, currentTroopLevel, field, value) {
    const key = `${slug}:${playerName}`
    const base = { ...parseTroop(currentTroopLevel), ...(troopEdits[key] || {}) }
    const next = { ...base, [field]: value }
    if (next.g && next.s && next.m) {
      setTroopEdits(prev => {
        const { [key]: _drop, ...rest } = prev
        return rest
      })
      handleTroopLevelChange(slug, playerName, `G${next.g} S${next.s} M${next.m}`)
    } else {
      setTroopEdits(prev => ({ ...prev, [key]: next }))
    }
  }

  async function handlePopulateFromChests(slug) {
    const { synced, removed } = await api.dashboardAncientsPopulateFromChests(slug)
    setPopulateMsg(prev => ({ ...prev, [slug]: cx.populateFromChestsResult(synced, removed) }))
    setConfirmPopulate(prev => ({ ...prev, [slug]: false }))
    setTimeout(() => setPopulateMsg(prev => ({ ...prev, [slug]: '' })), 5000)
    refresh()
  }

  async function handleDeleteRosterEntry(slug, playerName) {
    const key = `${slug}:${playerName}`
    await api.dashboardAncientsDeleteRosterEntry(slug, playerName)
    setConfirmDeleteRoster(prev => ({ ...prev, [key]: false }))
    refresh()
  }

  async function handleClearOcrImport(slug) {
    const { deleted, cleared } = await api.dashboardAncientsClearOcrImport(slug)
    setConfirmClearOcr(prev => ({ ...prev, [slug]: false }))
    setClearOcrMsg(prev => ({ ...prev, [slug]: `Удалено: ${deleted}, очищено: ${cleared}` }))
    setTimeout(() => setClearOcrMsg(prev => ({ ...prev, [slug]: '' })), 5000)
    refresh()
  }

  async function handleAddManual(slug, useNameOverride) {
    const form = manualForm[slug] || {}
    const name = useNameOverride || form.name
    if (!name) return
    try {
      await api.dashboardAncientsAddManual(slug, {
        player_name: name, troop_level: form.troop_level || null, rank: form.rank || null,
      })
      setManualForm(prev => ({ ...prev, [slug]: {} }))
      setManualSimilar(prev => ({ ...prev, [slug]: null }))
      refresh()
    } catch (e) {
      if (e.similarName) {
        setManualSimilar(prev => ({ ...prev, [slug]: e.similarName }))
      } else {
        alert(e.message || cx.manualDuplicateError)
      }
    }
  }

  async function handleCreateClan() {
    if (!createForm.kingdom.trim() || !createForm.clan.trim()) return
    setCreating(true)
    setCreateError('')
    try {
      await api.dashboardAncientsCreate(createForm.kingdom.trim(), createForm.clan.trim())
      setShowCreateModal(false)
      setCreateForm({ kingdom: '', clan: '' })
      refresh()
    } catch (e) {
      setCreateError(e.message || cx.createClanError)
    } finally {
      setCreating(false)
    }
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
    try {
      const result = await api.dashboardAncientsCalculate(slug, payload)
      setResultByCollector(prev => ({ ...prev, [slug]: result }))
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка расчёта')
    }
  }

  if (loadError) return <div className="page-content text-muted" style={{ maxWidth: 1600 }}>{loadError}</div>
  if (!collectors) return <div className="page-content text-muted" style={{ maxWidth: 1600 }}>...</div>

  return (
    <div className="page-content" style={{ maxWidth: 1600 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{cx.title}</h2>
        <button className="btn-secondary" style={{ fontSize: 13 }} onClick={() => setShowCreateModal(true)}>
          {cx.createClanBtn}
        </button>
      </div>

      {showCreateModal && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setShowCreateModal(false)}
        >
          <div
            className="card"
            style={{ width: 360, maxWidth: '90vw' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontWeight: 600, marginBottom: 16 }}>{cx.createClanTitle}</div>
            <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12, marginBottom: 12 }}>
              {cx.createClanKingdomLabel}
              <input
                className="input-dark"
                value={createForm.kingdom}
                onChange={e => setCreateForm(prev => ({ ...prev, kingdom: e.target.value }))}
                autoFocus
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', fontSize: 12, marginBottom: 16 }}>
              {cx.createClanClanLabel}
              <input
                className="input-dark"
                value={createForm.clan}
                onChange={e => setCreateForm(prev => ({ ...prev, clan: e.target.value }))}
              />
            </label>
            {createError && (
              <div style={{ color: '#F87171', fontSize: 12, marginBottom: 12 }}>{createError}</div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                {cx.createClanCancel}
              </button>
              <button className="btn-primary" disabled={creating} onClick={handleCreateClan}>
                {cx.createClanSubmit}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="chest-tabs" style={{ marginBottom: 24 }}>
        <button className={`chest-tab ${activeTab === 'clans' ? 'chest-tab--active' : ''}`}
                onClick={() => setActiveTab('clans')}>{cx.tabClans}</button>
        <button className={`chest-tab ${activeTab === 'help' ? 'chest-tab--active' : ''}`}
                onClick={() => setActiveTab('help')}>{cx.tabHowItWorks}</button>
      </div>

      {activeTab === 'help' && (
        <div style={{ maxWidth: 760 }}>
          <p className="text-muted" style={{ marginBottom: 24, fontSize: 15, lineHeight: 1.6 }}>{cx.howItWorksIntro}</p>
          {cx.howItWorksSections.map((s, i) => (
            <div key={i} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 16, marginBottom: 6 }}>{s.title}</h3>
              <p className="text-muted" style={{ fontSize: 14, lineHeight: 1.6, margin: 0 }}>{s.body}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'clans' && (<>
      {joinMessage && (
        <div style={{
          marginBottom: 16, padding: '10px 16px', borderRadius: 8,
          background: joinMessage === cx.joinSuccess ? 'rgba(166,227,161,0.15)' : 'rgba(243,139,168,0.15)',
          border: `1px solid ${joinMessage === cx.joinSuccess ? '#a6e3a1' : '#f38ba8'}`,
          color: joinMessage === cx.joinSuccess ? '#a6e3a1' : '#f38ba8',
        }}>
          {joinMessage}
        </div>
      )}

      {collectors.length === 0 && (
        <div className="card" style={{ marginTop: 12, textAlign: 'center', padding: 32 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>{cx.emptyStateTitle}</div>
          <div className="text-muted" style={{ marginBottom: 16 }}>{cx.emptyStateBody}</div>
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            {cx.createClanBtn}
          </button>
        </div>
      )}

      {collectors.map(c => {
        const form = formByCollector[c.slug] || DEFAULT_FORM
        const result = resultByCollector[c.slug]
        const levels = levelsFor(form)
        const maxStartLevel = 250 - (form.summonCount - 1)

        const sort = sortByCollector[c.slug] || { field: 'place', dir: 'asc' }
        const sortArrow = field => sort.field === field ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''
        const sortedRoster = [...(c.roster || [])].sort((a, b) => {
          if (sort.field === 'name') {
            const na = (a.player_name || '').toLowerCase()
            const nb = (b.player_name || '').toLowerCase()
            return sort.dir === 'asc' ? na.localeCompare(nb, 'ru') : nb.localeCompare(na, 'ru')
          }
          const pa = a.place ?? 999
          const pb = b.place ?? 999
          return sort.dir === 'asc' ? pa - pb : pb - pa
        })

        const srcSlug = canonicalSourceSlug[c.slug] ?? c.slug
        const srcNames = (canonicalSources.find(s => s.slug === srcSlug)?.canonical_names)
          ?? (c.canonical_names ?? [])

        return (
          <div key={c.slug} style={{ marginBottom: 32 }}>
            <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>{c.kingdom} / {c.clan}</span>
              {c.public_url && (
                <a href={c.public_url} target="_blank" rel="noreferrer"
                   style={{ fontSize: 12, color: 'var(--on-surface2)' }}>
                  {cx.publicLink}
                </a>
              )}
              {!c.is_owner && (
                <span style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 12,
                  background: 'rgba(137,180,250,0.15)', border: '1px solid #89b4fa',
                  color: '#89b4fa', fontWeight: 600,
                }}>
                  {cx.editorBadge}
                </span>
              )}
              {c.is_owner && (
                <button
                  className="btn-secondary"
                  style={{ fontSize: 12, padding: '4px 12px' }}
                  onClick={() => handleInvite(c.slug)}
                >
                  {inviteMsg[c.slug] || cx.inviteBtn}
                </button>
              )}
              {c.is_owner && (
                confirmHideByCollector[c.slug] ? (
                  <>
                    <span style={{ fontSize: 12, color: '#F87171' }}>{cx.hideConfirm}</span>
                    <button
                      className="btn-primary"
                      style={{ fontSize: 12, padding: '3px 10px', background: '#DC2626', boxShadow: 'none' }}
                      onClick={() => handleSetHidden(c.slug, true)}
                    >{cx.hideYes}</button>
                    <button
                      className="btn-secondary"
                      style={{ fontSize: 12, padding: '3px 10px' }}
                      onClick={() => setConfirmHideByCollector(prev => ({ ...prev, [c.slug]: false }))}
                    >{cx.closeSeasonNo}</button>
                  </>
                ) : (
                  <button
                    className="btn-secondary"
                    style={{ fontSize: 12, padding: '4px 12px', color: '#F87171', borderColor: '#F8717144' }}
                    onClick={() => setConfirmHideByCollector(prev => ({ ...prev, [c.slug]: true }))}
                  >{cx.hideBtn}</button>
                )
              )}
            </div>

            {/* ── Калькулятор (только для владельца) ── */}
            {c.is_owner && <div className="card" style={{ marginBottom: 16 }}>
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
                      {(c.presets || []).map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </label>
                </div>
              )}

              <button className="btn-primary" onClick={() => handleCalculate(c.slug)}>
                {cx.calculateButton}
              </button>
            </div>}

            {result && c.is_owner && (
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
                      {(result.result.players || []).map(p => (
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

            {/* ── Ростер клана ── */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
                <label style={{ fontSize: 13, color: '#a6adc8', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>Точность: {Math.round(fuzzyThreshold * 100)}%</span>
                  <input
                    type="range" min={50} max={100} step={5}
                    value={Math.round(fuzzyThreshold * 100)}
                    onChange={e => {
                      const val = parseInt(e.target.value) / 100
                      setFuzzyThreshold(val)
                      refresh(val)
                    }}
                    style={{ width: 120 }}
                  />
                </label>
                {canonicalSources.length > 1 && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#a6adc8' }}>
                    Имена из:
                    <select
                      className="input-dark"
                      value={srcSlug}
                      onChange={e => setCanonicalSourceSlug(prev => ({ ...prev, [c.slug]: e.target.value }))}
                      style={{ minWidth: 120 }}
                    >
                      {canonicalSources.map(s => (
                        <option key={s.slug} value={s.slug}>{s.clan}</option>
                      ))}
                    </select>
                  </label>
                )}
              </div>

              {c.is_owner && (
                <div className="ancient-thresholds-row" style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{cx.thresholdsTitle}:</span>
                  <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                    {cx.thresholdLight}
                    <input type="number" className="input-dark" style={{ width: 60 }}
                      value={c.quota_thresholds.light_pct}
                      onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'light_pct', e.target.value)} />
                  </label>
                  <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                    {cx.thresholdMedium}
                    <input type="number" className="input-dark" style={{ width: 60 }}
                      value={c.quota_thresholds.medium_pct}
                      onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'medium_pct', e.target.value)} />
                  </label>
                  <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                    {cx.thresholdCritical}
                    <input type="number" className="input-dark" style={{ width: 60 }}
                      value={c.quota_thresholds.critical_pct}
                      onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'critical_pct', e.target.value)} />
                  </label>
                </div>
              )}

              <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontWeight: 600 }}>{cx.rosterTitle}</span>
                {confirmClearOcr[c.slug] ? (
                  <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: '#f9a825' }}>Стереть турнирные очки?</span>
                    <button
                      style={{ fontSize: 11, padding: '2px 6px', background: '#DC2626', border: 'none', color: '#fff', borderRadius: 4 }}
                      onClick={() => handleClearOcrImport(c.slug)}
                    >{cx.deleteRosterYes}</button>
                    <button
                      style={{ fontSize: 11, padding: '2px 6px', background: 'transparent', border: '1px solid #6c7086', color: '#6c7086', borderRadius: 4 }}
                      onClick={() => setConfirmClearOcr(prev => ({ ...prev, [c.slug]: false }))}
                    >{cx.closeSeasonNo}</button>
                  </span>
                ) : (
                  <button
                    style={{ fontSize: 11, padding: '2px 8px', cursor: 'pointer', background: 'transparent', border: '1px solid #6c7086', color: '#6c7086', borderRadius: 4 }}
                    onClick={() => setConfirmClearOcr(prev => ({ ...prev, [c.slug]: true }))}
                  >
                    Очистить
                  </button>
                )}
                {clearOcrMsg[c.slug] && (
                  <span style={{ fontSize: 12, color: '#a6e3a1' }}>{clearOcrMsg[c.slug]}</span>
                )}
              </div>

              {sortedRoster.length === 0 ? (
                <div className="text-muted">{cx.noRoster}</div>
              ) : (
                <div className="ancient-roster-wrap">
                <table className="chest-table ancient-roster-table">
                  <thead>
                    <tr>
                      <th>№</th>
                      <th
                        style={{ cursor: 'pointer', userSelect: 'none' }}
                        onClick={() => toggleSort(c.slug, 'name')}
                      >
                        Имя{sortArrow('name')}
                      </th>
                      <th>{cx.rank}</th>
                      <th>{cx.troopLevel}</th>
                      <th
                        style={{ cursor: 'pointer', userSelect: 'none' }}
                        onClick={() => toggleSort(c.slug, 'place')}
                      >
                        {cx.place}{sortArrow('place')}
                      </th>
                      <th>{cx.points}</th>
                      <th>{cx.quota}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedRoster.map((p, idx) => {
                      const suggestion = srcSlug === c.slug
                        ? (p.suggested_name || '')
                        : (clientFuzzyMatch(p.player_name, srcNames, fuzzyThreshold) || '')
                      const pending = (pendingMappings[c.slug] || {})[p.player_name]
                      const deleteKey = `${c.slug}:${p.player_name}`
                      return (
                        <tr key={p.player_name}
                          className={rowShortfallClass(p.shortfall_pct, c.quota_thresholds)}>
                          <td>{idx + 1}</td>
                          <td>
                            {(() => {
                              const rowKey = `${c.slug}:${p.player_name}`
                              return (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                  <span style={{ fontWeight: 600 }}>{p.raw_ocr_name || p.player_name}</span>
                                  {p.mapping_confirmed ? (
                                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                      <span style={{ color: '#a6e3a1', fontWeight: 600, fontSize: 12 }}>✅ {p.mapped_name}</span>
                                      {p.raw_ocr_name && p.raw_ocr_name !== p.player_name ? (
                                        <span title="Слияние необратимо" style={{ fontSize: 12 }}>🔒</span>
                                      ) : (
                                        <button
                                          style={{
                                            fontSize: 11, padding: '1px 6px', cursor: 'pointer',
                                            background: 'transparent', border: '1px solid #6c7086',
                                            color: '#6c7086', borderRadius: 4,
                                          }}
                                          onClick={async () => {
                                            await api.dashboardAncientsNameMappingDelete(c.slug, p.raw_ocr_name || p.player_name)
                                            refresh()
                                          }}
                                        >
                                          Разблокировать
                                        </button>
                                      )}
                                    </span>
                                  ) : mappingEditOpen[rowKey] ? (
                                    <select
                                      className="input-dark"
                                      autoFocus
                                      value={pending !== undefined ? pending : suggestion}
                                      onChange={e => setPendingMappings(prev => ({
                                        ...prev,
                                        [c.slug]: { ...(prev[c.slug] || {}), [p.player_name]: e.target.value },
                                      }))}
                                      style={{ minWidth: 160 }}
                                    >
                                      <option value="">— не сопоставлять —</option>
                                      {srcNames.map(name => (
                                        <option key={name} value={name}>{name}</option>
                                      ))}
                                    </select>
                                  ) : (
                                    <button
                                      style={{
                                        fontSize: 11, padding: '1px 6px', cursor: 'pointer', alignSelf: 'flex-start',
                                        background: 'transparent', border: '1px solid #6c7086',
                                        color: '#6c7086', borderRadius: 4,
                                      }}
                                      onClick={() => setMappingEditOpen(prev => ({ ...prev, [rowKey]: true }))}
                                    >
                                      🔗 {pending ? pending : 'Сопоставить'}
                                    </button>
                                  )}
                                </div>
                              )
                            })()}
                          </td>
                          <td>
                            <select className="input-dark" value={p.rank || ''}
                              style={{ width: 100 }}
                              onChange={e => handleRankChange(c.slug, p.player_name, e.target.value)}>
                              {RANKS.map(r => <option key={r} value={r}>{r || cx.noTroopLevel}</option>)}
                            </select>
                          </td>
                          <td>
                            {(() => {
                              const key = `${c.slug}:${p.player_name}`
                              const troop = { ...parseTroop(p.troop_level), ...(troopEdits[key] || {}) }
                              return (
                                <div style={{ display: 'flex', gap: 3, alignItems: 'center', flexWrap: 'nowrap' }}>
                                  <select className="input-dark" value={troop.g} style={{ width: 44 }}
                                    onChange={e => handleTroopFieldChange(c.slug, p.player_name, p.troop_level, 'g', e.target.value)}>
                                    <option value="">G</option>
                                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                                  </select>
                                  <select className="input-dark" value={troop.s} style={{ width: 44 }}
                                    onChange={e => handleTroopFieldChange(c.slug, p.player_name, p.troop_level, 's', e.target.value)}>
                                    <option value="">S</option>
                                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                                  </select>
                                  <select className="input-dark" value={troop.m} style={{ width: 44 }}
                                    onChange={e => handleTroopFieldChange(c.slug, p.player_name, p.troop_level, 'm', e.target.value)}>
                                    <option value="">M</option>
                                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                                  </select>
                                  {troop.g && troop.s && troop.m
                                    ? <span style={{ fontSize: 13, fontWeight: 700, color: '#f9a825', marginLeft: 6, whiteSpace: 'nowrap' }}>
                                        G{troop.g} S{troop.s} M{troop.m}
                                      </span>
                                    : <span style={{ fontSize: 12, color: '#6c7086', marginLeft: 6 }}>{cx.noTroopLevel}</span>
                                  }
                                </div>
                              )
                            })()}
                          </td>
                          <td>{p.place ?? '—'}</td>
                          <td>{p.points !== null && p.points !== undefined ? fmtNum(p.points, 0) : '—'}</td>
                          <td>{p.quota != null ? fmtNum(p.quota, 2) : '—'}</td>
                          <td>
                            {confirmDeleteRoster[deleteKey] ? (
                              <span style={{ display: 'flex', gap: 4, alignItems: 'center', whiteSpace: 'nowrap' }}>
                                <button
                                  style={{ fontSize: 11, padding: '2px 6px', background: '#DC2626', border: 'none', color: '#fff', borderRadius: 4 }}
                                  onClick={() => handleDeleteRosterEntry(c.slug, p.player_name)}
                                >{cx.deleteRosterYes}</button>
                                <button
                                  style={{ fontSize: 11, padding: '2px 6px', background: 'transparent', border: '1px solid #6c7086', color: '#6c7086', borderRadius: 4 }}
                                  onClick={() => setConfirmDeleteRoster(prev => ({ ...prev, [deleteKey]: false }))}
                                >{cx.closeSeasonNo}</button>
                              </span>
                            ) : (
                              <button
                                style={{ fontSize: 11, padding: '2px 6px', background: 'transparent', border: '1px solid #F8717144', color: '#F87171', borderRadius: 4 }}
                                onClick={() => setConfirmDeleteRoster(prev => ({ ...prev, [deleteKey]: true }))}
                              >{cx.deleteRosterBtn}</button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                </div>
              )}

              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--outline)' }}>
                {confirmPopulate[c.slug] ? (
                  <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: '#F87171' }}>{cx.populateFromChestsConfirm}</span>
                    <button className="btn-primary" style={{ fontSize: 12, padding: '3px 10px', background: '#DC2626', boxShadow: 'none' }}
                      onClick={() => handlePopulateFromChests(c.slug)}>
                      {cx.populateFromChestsYes}
                    </button>
                    <button className="btn-secondary" style={{ fontSize: 12, padding: '3px 10px' }}
                      onClick={() => setConfirmPopulate(prev => ({ ...prev, [c.slug]: false }))}>
                      {cx.closeSeasonNo}
                    </button>
                  </div>
                ) : (
                  <button className="btn-secondary" style={{ fontSize: 13, marginBottom: 12 }}
                    onClick={() => setConfirmPopulate(prev => ({ ...prev, [c.slug]: true }))}>
                    {populateMsg[c.slug] || cx.populateFromChestsBtn}
                  </button>
                )}
                <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.manualAddTitle}</div>
                {manualSimilar[c.slug] && (
                  <div style={{ marginBottom: 8, fontSize: 13, color: '#f9a825' }}>
                    {cx.manualSimilarNameWarning(manualSimilar[c.slug])}
                    <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 8, padding: '2px 8px' }}
                      onClick={() => handleAddManual(c.slug, manualSimilar[c.slug])}>
                      {cx.manualUseSuggested}
                    </button>
                    <button className="btn-secondary" style={{ fontSize: 12, marginLeft: 4, padding: '2px 8px' }}
                      onClick={() => setManualSimilar(prev => ({ ...prev, [c.slug]: null }))}>
                      {cx.manualAddAnyway}
                    </button>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <input
                    className="input-dark"
                    placeholder={cx.manualNamePlaceholder}
                    value={(manualForm[c.slug] || {}).name || ''}
                    onChange={e => setManualForm(prev => ({ ...prev, [c.slug]: { ...(prev[c.slug] || {}), name: e.target.value } }))}
                    style={{ minWidth: 140 }}
                  />
                  <select className="input-dark"
                    value={(manualForm[c.slug] || {}).rank || ''}
                    onChange={e => setManualForm(prev => ({ ...prev, [c.slug]: { ...(prev[c.slug] || {}), rank: e.target.value } }))}>
                    {RANKS.map(r => <option key={r} value={r}>{r || cx.manualRankLabel}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).g || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), g: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">G</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).s || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), s: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">S</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <select className="input-dark" style={{ width: 44 }}
                    value={(manualForm[c.slug] || {}).m || ''}
                    onChange={e => setManualForm(prev => {
                      const f = { ...(prev[c.slug] || {}), m: e.target.value }
                      return { ...prev, [c.slug]: { ...f, troop_level: (f.g && f.s && f.m) ? `G${f.g} S${f.s} M${f.m}` : undefined } }
                    })}>
                    <option value="">M</option>
                    {TIERS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <button className="btn-primary" onClick={() => handleAddManual(c.slug)}>
                    {cx.manualAddButton}
                  </button>
                </div>
              </div>

              <button
                className="btn-primary"
                style={{ marginTop: 12 }}
                onClick={async () => {
                  const pending = pendingMappings[c.slug] || {}
                  const mappings = Object.entries(pending)
                    .filter(([, canonical]) => canonical)
                    .map(([raw_ocr_name, canonical_name]) => ({ raw_ocr_name, canonical_name, confirmed: true }))
                  if (mappings.length === 0) return
                  await api.dashboardAncientsNameMappings(c.slug, mappings)
                  setPendingMappings(prev => ({ ...prev, [c.slug]: {} }))
                  refresh()
                }}
              >
                Сохранить маппинги
              </button>
            </div>

            {/* ── История расчётов ── */}
            <div className="card" style={{ marginTop: 16 }}>
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
          </div>
        )
      })}

      {hiddenCollectors.length > 0 && (
        <div className="card" style={{ marginTop: 8 }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>
            {cx.hiddenSectionTitle} ({hiddenCollectors.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {hiddenCollectors.map(h => (
              <div key={h.slug} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="text-muted">{h.kingdom} / {h.clan}</span>
                <button
                  className="btn-secondary"
                  style={{ fontSize: 12, padding: '3px 10px' }}
                  onClick={() => handleSetHidden(h.slug, false)}
                >{cx.showBtn}</button>
              </div>
            ))}
          </div>
        </div>
      )}
      </>)}
    </div>
  )
}
