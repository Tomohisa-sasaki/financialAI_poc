
const ALL = [
  { group: "収益性", items: [
    { id:"ROE", label:"ROE" },
    { id:"ROA", label:"ROA" },
    { id:"OperatingMargin", label:"営業利益率" },
    { id:"NetMargin", label:"純利益率" },
    { id:"GrossMargin", label:"粗利率" },
  ]},
  { group: "安全性", items: [
    { id:"EquityRatio", label:"自己資本比率" },
  ]},
  { group: "成長性", items: [
    { id:"REVENUE_GROWTH", label:"売上成長率" },
  ]},
  { group: "規模", items: [
    { id:"REVENUE", label:"売上高" },
    { id:"OPERATINGINCOME", label:"営業利益" },
    { id:"NETINCOME", label:"当期純利益" },
  ]},
]
export default function IndicatorPicker({ selected, onChange }: { selected: string[], onChange: (v:string[])=>void }) {
  const toggle = (id: string) => selected.includes(id) ? onChange(selected.filter(x=>x!==id)) : onChange([...selected, id])
  return (
    <div className="card">
      <div className="font-semibold mb-2">財務指標</div>
      {ALL.map(g => (
        <div key={g.group} className="mb-2">
          <div className="text-sm text-gray-300 mb-1">{g.group}</div>
          <div className="flex flex-wrap gap-3">
            {g.item