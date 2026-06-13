import StatusBadge from './StatusBadge.jsx'

const FIELD_LABELS = {
  brand_name: 'Brand name',
  class_type: 'Class / type',
  alcohol_content: 'Alcohol content',
  net_contents: 'Net contents',
  producer_name: 'Producer name',
  producer_address: 'Producer address',
  country_of_origin: 'Country of origin',
  government_warning: 'Government warning',
}

function cellText(value) {
  if (value === null || value === undefined || value === '') {
    return <span className="text-slate-400 italic">— not found —</span>
  }
  return value
}

export default function FieldResultsTable({ fields, compact = false }) {
  if (!fields?.length) return null
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-300">
      <table className="w-full text-left bg-white">
        <thead>
          <tr className="bg-slate-100 text-sm text-slate-700">
            <th className="px-4 py-3 font-bold">Field</th>
            <th className="px-4 py-3 font-bold">You declared</th>
            <th className="px-4 py-3 font-bold">Found on label</th>
            <th className="px-4 py-3 font-bold">Result</th>
            {!compact && <th className="px-4 py-3 font-bold">Why</th>}
          </tr>
        </thead>
        <tbody>
          {fields.map((f) => (
            <tr key={f.field} className="border-t border-slate-200 align-top">
              <td className="px-4 py-3 font-semibold whitespace-nowrap">{FIELD_LABELS[f.field] || f.field}</td>
              <td className="px-4 py-3 max-w-xs break-words">
                {f.field === 'government_warning'
                  ? <span className="text-slate-600 text-xs leading-snug block">{f.declared}</span>
                  : cellText(f.declared)}
              </td>
              <td className="px-4 py-3 max-w-xs break-words">{cellText(f.extracted)}</td>
              <td className="px-4 py-3"><StatusBadge status={f.status} /></td>
              {!compact && <td className="px-4 py-3 text-sm text-slate-700 max-w-sm">{f.reason}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
