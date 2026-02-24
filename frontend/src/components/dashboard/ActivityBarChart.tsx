import { motion } from 'framer-motion';

const COLORS = {
  bar: '#E02C26',
  barMuted: 'rgba(224, 44, 38, 0.15)',
  text: '#2E3A56',
  textMuted: '#5A6B8A',
};

interface DataPoint {
  label: string;
  value: number;
  max: number;
}

interface ActivityBarChartProps {
  data: DataPoint[];
}

export function ActivityBarChart({ data }: ActivityBarChartProps) {
  const maxVal = Math.max(...data.map((d) => Math.max(d.value, d.max)), 1);

  return (
    <div className="space-y-4">
      {data.map((item, i) => {
        const pct = maxVal > 0 ? Math.min((item.value / maxVal) * 100, 100) : 0;
        return (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between text-xs">
              <span style={{ color: COLORS.textMuted }}>{item.label}</span>
              <span style={{ color: COLORS.text }} className="font-medium">
                {item.value}
              </span>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: COLORS.barMuted }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: COLORS.bar }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, delay: i * 0.08, ease: 'easeOut' }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
