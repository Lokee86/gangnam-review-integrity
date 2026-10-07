import { useMemo, useState } from 'react'

import reviewIntegrity from '../data/product/review-integrity.json'
import { Badge } from './components/Badge'
import { ConfidenceBar } from './components/ConfidenceBar'
import { SearchField } from './components/SearchField'
import { SegmentedControl } from './components/SegmentedControl'
import { StatCard } from './components/StatCard'

type ReviewRecord = {
  id: string
  clinic_id: string
  clinic_name: string
  review_date: string | null
  rating: number | null
  procedures: string[]
  primary_procedure: string | null
  revision: boolean
  procedure_signature: string | null
  source: string | null
  source_url: string
  summary: string
}

type PairEvidence = {
  left_id: string
  right_id: string
  match_probability: number
  embedding_cosine: number
  same_procedure_signature: boolean
  same_review_date: boolean
  same_rating: boolean
}

type Cluster = {
  cluster_id: string
  kind: 'duplicate_cluster' | 'singleton'
  clinic_id: string
  clinic_name: string
  member_count: number
  duplicate_record_count: number
  review_status: 'auto_linked' | 'needs_review'
  possible_internal_pairs: number
  accepted_edge_count: number
  edge_density: number
  transitive_only_pair_count: number
  representative_id: string
  procedure_signatures: string[]
  review_dates: string[]
  ratings: number[]
  score_summary: {
    accepted_edge_count: number
    min_match_probability: number
    mean_match_probability: number
    max_match_probability: number
  } | null
  accepted_pair_matches: PairEvidence[]
  records: ReviewRecord[]
}

type Dataset = {
  summary: {
    observed_reviews: number
    estimated_unique_experiences: number
    estimated_redundant_records: number
    duplicate_clusters: number
    singleton_reviews: number
    accepted_duplicate_edges: number
    clusters_requiring_review: number
    records_in_review_clusters: number
  }
  model: {
    name: string
    decision_threshold: number
    calibration_metrics: {
      precision: number
      recall: number
      f1: number
      roc_auc: number
      average_precision: number
    }
    calibration_note: string
  }
  clinic_stats: Array<{
    clinic_id: string
    clinic_name: string
    observed_reviews: number
    estimated_unique_experiences: number
    estimated_redundant_records: number
  }>
  duplicate_clusters: Cluster[]
  singletons: Cluster[]
}

const data = reviewIntegrity as Dataset

type View = 'duplicates' | 'review' | 'all'

const viewOptions = [
  { id: 'duplicates', label: 'Likely duplicates' },
  { id: 'review', label: 'Needs review' },
  { id: 'all', label: 'All clusters' },
] as const

function formatProcedure(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase())
}

function formatDate(value: string | null) {
  if (!value) return 'No date'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(
    new Date(value + 'T00:00:00')
  )
}

function ClusterCard({ cluster }: { cluster: Cluster }) {
  const [open, setOpen] = useState(cluster.review_status === 'needs_review')
  const meanProbability = cluster.score_summary?.mean_match_probability ?? 0

  return (
    <article className={`cluster-card ${cluster.review_status === 'needs_review' ? 'cluster-card--review' : ''}`}>
      <button className="cluster-card__header" onClick={() => setOpen(value => !value)} type="button">
        <div className="cluster-card__identity">
          <div className="cluster-card__eyebrow">
            <span>{cluster.cluster_id}</span>
            {cluster.review_status === 'needs_review' ? (
              <Badge tone="warning">Needs review</Badge>
            ) : (
              <Badge tone="success">Auto-linked</Badge>
            )}
          </div>
          <h3>{cluster.clinic_name}</h3>
          <div className="cluster-card__meta">
            <span>{cluster.member_count} review records</span>
            <span>•</span>
            <span>{cluster.duplicate_record_count} likely syndicated copies</span>
            <span>•</span>
            <span>{cluster.procedure_signatures.map(formatProcedure).join(' + ') || 'Unclassified'}</span>
          </div>
        </div>

        <div className="cluster-card__score">
          <div className="cluster-card__score-label">Mean match</div>
          <ConfidenceBar value={meanProbability} />
          <span className="cluster-card__chevron" aria-hidden="true">{open ? '−' : '+'}</span>
        </div>
      </button>

      {open ? (
        <div className="cluster-card__body">
          {cluster.review_status === 'needs_review' ? (
            <div className="review-callout">
              <strong>Ambiguous connected component.</strong>
              <span>
                {cluster.accepted_edge_count} of {cluster.possible_internal_pairs} possible internal pairs crossed the
                model threshold. {cluster.transitive_only_pair_count} relationship
                {cluster.transitive_only_pair_count === 1 ? ' is' : 's are'} transitive only.
              </span>
            </div>
          ) : null}

          <div className="records-grid">
            {cluster.records.map(record => (
              <section className="review-record" key={record.id}>
                <div className="review-record__topline">
                  <span className="review-record__id">{record.id.split('-').at(-1)}</span>
                  <span>{formatDate(record.review_date)}</span>
                  <span>{record.rating ? `${record.rating.toFixed(1)} ★` : 'No rating'}</span>
                </div>
                <div className="review-record__tags">
                  {record.procedures.map(procedure => (
                    <span className="procedure-tag" key={procedure}>{formatProcedure(procedure)}</span>
                  ))}
                  {record.revision ? <span className="procedure-tag procedure-tag--revision">Revision</span> : null}
                </div>
                <p>{record.summary}</p>
                <div className="review-record__source">Source: {record.source ?? 'Unknown'}</div>
              </section>
            ))}
          </div>

          {cluster.accepted_pair_matches.length ? (
            <div className="evidence-table">
              <div className="evidence-table__heading">
                <span>Matched pair</span>
                <span>Probability</span>
                <span>Semantic</span>
                <span>Procedure</span>
                <span>Date</span>
                <span>Rating</span>
              </div>
              {cluster.accepted_pair_matches.map(pair => (
                <div className="evidence-table__row" key={`${pair.left_id}-${pair.right_id}`}>
                  <span>{pair.left_id.split('-').at(-1)} ↔ {pair.right_id.split('-').at(-1)}</span>
                  <span>{Math.round(pair.match_probability * 100)}%</span>
                  <span>{Math.round(pair.embedding_cosine * 100)}%</span>
                  <span>{pair.same_procedure_signature ? 'Match' : 'Different'}</span>
                  <span>{pair.same_review_date ? 'Match' : 'Different'}</span>
                  <span>{pair.same_rating ? 'Match' : 'Different'}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}

export function App() {
  const [view, setView] = useState<View>('duplicates')
  const [query, setQuery] = useState('')
  const [clinic, setClinic] = useState('all')

  const allClusters = useMemo(() => [...data.duplicate_clusters, ...data.singletons] as Cluster[], [])

  const visibleClusters = useMemo(() => {
    const term = query.trim().toLowerCase()
    return allClusters.filter(cluster => {
      if (view === 'duplicates' && cluster.member_count < 2) return false
      if (view === 'review' && cluster.review_status !== 'needs_review') return false
      if (clinic !== 'all' && cluster.clinic_id !== clinic) return false

      if (!term) return true
      const haystack = [
        cluster.clinic_name,
        ...cluster.procedure_signatures,
        ...cluster.records.flatMap(record => [record.summary, ...record.procedures]),
      ].join(' ').toLowerCase()
      return haystack.includes(term)
    })
  }, [allClusters, clinic, query, view])

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <div className="hero__kicker">Gangnam Beauty Guide · Review Integrity Explorer</div>
          <h1>See the reviews. <span>See the repetition.</span></h1>
          <p>
            A linkage prototype that groups likely syndicated review copies so buyers can distinguish
            observed review volume from estimated underlying patient experiences.
          </p>
        </div>
        <div className="hero__model">
          <Badge tone="info">Procedure-aware linkage</Badge>
          <strong>F1 {data.model.calibration_metrics.f1.toFixed(3)}</strong>
          <span>
            {(data.model.calibration_metrics.precision * 100).toFixed(1)}% precision ·{' '}
            {(data.model.calibration_metrics.recall * 100).toFixed(1)}% recall
          </span>
        </div>
      </header>

      <section className="stats-grid" aria-label="Review integrity summary">
        <StatCard label="Observed reviews" value={data.summary.observed_reviews} detail="Raw records in the snapshot" />
        <StatCard
          label="Estimated unique experiences"
          value={data.summary.estimated_unique_experiences}
          detail="Connected components at calibrated threshold"
        />
        <StatCard
          label="Estimated redundant records"
          value={data.summary.estimated_redundant_records}
          detail="Likely syndicated or repeated copies"
        />
        <StatCard
          label="Needs manual review"
          value={data.summary.clusters_requiring_review}
          detail={`${data.summary.records_in_review_clusters} records in ambiguous clusters`}
        />
      </section>

      <section className="integrity-panel">
        <div className="integrity-panel__copy">
          <span className="integrity-panel__label">Snapshot signal</span>
          <strong>{Math.round((data.summary.estimated_redundant_records / data.summary.observed_reviews) * 100)}%</strong>
          <p>of observed records collapse into already-represented experiences at the current model threshold.</p>
        </div>
        <div className="integrity-panel__bar" aria-hidden="true">
          <div
            className="integrity-panel__bar-fill"
            style={{ width: `${(data.summary.estimated_redundant_records / data.summary.observed_reviews) * 100}%` }}
          />
        </div>
        <p className="integrity-panel__note">
          Model estimate, not verified patient identity. Two larger connected components are explicitly flagged for review.
        </p>
      </section>

      <section className="workspace">
        <aside className="clinic-sidebar">
          <div className="clinic-sidebar__title">Clinics</div>
          <button
            className={clinic === 'all' ? 'clinic-row is-active' : 'clinic-row'}
            onClick={() => setClinic('all')}
            type="button"
          >
            <span>All clinics</span>
            <strong>{data.summary.observed_reviews}</strong>
          </button>
          {data.clinic_stats.map(item => (
            <button
              className={clinic === item.clinic_id ? 'clinic-row is-active' : 'clinic-row'}
              key={item.clinic_id}
              onClick={() => setClinic(item.clinic_id)}
              type="button"
            >
              <span>
                {item.clinic_name}
                <small>{item.estimated_unique_experiences} est. unique</small>
              </span>
              <strong>{item.observed_reviews}</strong>
            </button>
          ))}
        </aside>

        <div className="cluster-workspace">
          <div className="toolbar">
            <SegmentedControl options={viewOptions} value={view} onChange={setView} />
            <SearchField value={query} onChange={setQuery} placeholder="Search clinic, procedure, or review text" />
          </div>

          <div className="cluster-list-heading">
            <div>
              <strong>{visibleClusters.length}</strong> cluster{visibleClusters.length === 1 ? '' : 's'}
            </div>
            <span>Click a cluster to inspect source reviews and match evidence.</span>
          </div>

          <div className="cluster-list">
            {visibleClusters.map(cluster => <ClusterCard cluster={cluster} key={cluster.cluster_id} />)}
          </div>
        </div>
      </section>

      <footer>
        Calibration set: 493 same-clinic candidate pairs · 45 manually adjudicated duplicate pairs · threshold selected on this same label set.
      </footer>
    </main>
  )
}
