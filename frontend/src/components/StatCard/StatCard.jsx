export default function StatCard({ stat }) {
  return <article className="stat-card"><div className={`stat-icon text-bg-${stat.tone}`}><i className={`bi ${stat.icon}`} /></div><div><p>{stat.label}</p><h2>{stat.value}</h2><span>{stat.note}</span></div></article>
}
