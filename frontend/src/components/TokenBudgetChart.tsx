import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { TokenBudget } from '../types'

interface Props {
  budget: TokenBudget
}

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444']
const LABELS = ['Document', 'System Prompt', 'History', 'Response Buffer']

export function TokenBudgetChart({ budget }: Props) {
  const data = [
    { name: LABELS[0], value: budget.allocations.document_content },
    { name: LABELS[1], value: budget.allocations.system_prompt },
    { name: LABELS[2], value: budget.allocations.conversation_history },
    { name: LABELS[3], value: budget.allocations.response_buffer },
  ]

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
      <h3 className="font-semibold text-gray-700 mb-4 text-sm uppercase tracking-wide">
        Token Budget — {budget.total_window.toLocaleString()} tokens total
      </h3>

      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number) => [`${v.toLocaleString()} tokens`, '']}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span className="text-xs text-gray-600">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
        <span>
          Utilization:{' '}
          <strong className="text-gray-800">{budget.document.utilization_pct}%</strong>
        </span>
        {budget.document.truncated && (
          <span className="text-amber-600 font-medium">⚠ Content truncated to fit</span>
        )}
      </div>
    </div>
  )
}
