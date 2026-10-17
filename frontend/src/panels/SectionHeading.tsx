export function SectionHeading({ index, title, note }: { index: string; title: string; note?: string }) {
  return <div className="section-heading"><span className="section-index">{index}</span><h2>{title}</h2>{note && <span className="section-note">{note}</span>}</div>
}
