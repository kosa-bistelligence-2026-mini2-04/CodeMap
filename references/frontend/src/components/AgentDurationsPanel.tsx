"use client";

interface AgentDurationsPanelProps {
  durations: Record<string, number>;
}

export function AgentDurationsPanel({ durations }: AgentDurationsPanelProps) {
  const entries = Object.entries(durations).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0);

  if (entries.length === 0) return null;

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-neutral-900">Agent Processing Time</h3>
        <p className="text-[10px] text-neutral-400 mt-1">
          Detailed pipeline execution breakdown across specialized agents.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs text-neutral-800">
          <thead>
            <tr className="text-left text-neutral-400 font-semibold border-b border-neutral-100">
              <th className="pb-2">Agent</th>
              <th className="pb-2">Duration</th>
              <th className="pb-2">Percentage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {entries.map(([name, ms]) => (
              <tr key={name} className="hover:bg-neutral-50/50 transition-colors">
                <td className="py-2.5 font-medium pr-4">{name}</td>
                <td className="py-2.5 pr-4 text-neutral-600">{(ms / 1000).toFixed(2)}s</td>
                <td className="py-2.5 text-neutral-500 font-semibold">
                  {total > 0 ? ((ms / total) * 100).toFixed(1) : "0"}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
