import { motion } from 'framer-motion'
import type { TierInfo } from '../types'

const TIER_BG: Record<number, string> = {
  1: 'bg-green-100 text-green-800 border-green-300',
  2: 'bg-blue-100 text-blue-800 border-blue-300',
  3: 'bg-amber-100 text-amber-800 border-amber-300',
  4: 'bg-red-100 text-red-800 border-red-300',
}

interface Props {
  tier: TierInfo
  tokenCount: number
}

export function TierBadge({ tier, tokenCount }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex flex-col gap-1 px-4 py-3 rounded-xl border-2 font-semibold ${TIER_BG[tier.tier]}`}
    >
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: tier.color }}
        />
        <span className="text-sm uppercase tracking-wide">Tier {tier.tier}</span>
        <span className="text-xs font-normal opacity-70">— {tier.label}</span>
      </div>
      <p className="text-xs font-normal leading-snug opacity-80 max-w-xs">{tier.description}</p>
      <p className="text-xs font-mono mt-1">{tokenCount.toLocaleString()} tokens</p>
    </motion.div>
  )
}
