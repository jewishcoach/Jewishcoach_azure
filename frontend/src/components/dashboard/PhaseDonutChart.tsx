import { motion } from 'framer-motion';

const PHASE_COLORS = ['#0EA5E9', '#38BDF8', '#7DD3FC', '#BAE6FD', '#FACC15', '#FDE047', '#A3A3A3'];
const COLORS = { text: '#1E293B', textMuted: '#64748B' };

interface PhaseCount {
  phase: string;
  label: string;
  count: number;
}

interface PhaseDonutChartProps {
  data: PhaseCount[];
  size?: number;
}

export function PhaseDonutChart({ data, size = 140 }: PhaseDonutChartProps) {
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const strokeWidth = size * 0.2;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;
  const segments = data.map((d, i) => {
    const pct = d.count / total;
    const strokeDasharray = `${pct * circumference} ${circumference}`;
    const strokeDashoffset = -offset;
    offset += pct * circumference;

    return {
      ...d,
      color: PHASE_COLORS[i % PHASE_COLORS.length],
      strokeDasharray,
      strokeDashoffset,
      pct: Math.round(pct * 100),
    };
  });

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {segments.map((seg, i) => (
            <motion.circle
              key={i}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={seg.strokeDasharray}
              strokeDashoffset={seg.strokeDashoffset}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: seg.strokeDashoffset }}
              transition={{ duration: 0.8, delay: i * 0.05, ease: 'easeOut' }}
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-2xl font-semibold" style={{ color: COLORS.text }}>{total}</div>
            <div className="text-xs" style={{ color: COLORS.textMuted }}>שיחות</div>
          </div>
        </div>
      </div>
      <div className="flex flex-wrap justify-center gap-x-4 gap-y-1">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs">
            <div className="w-2 h-2 rounded-full" style={{ background: seg.color }} />
            <span style={{ color: COLORS.textMuted }}>{seg.label}</span>
            <span style={{ color: COLORS.text }} className="font-medium">{seg.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
