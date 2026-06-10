import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface AgentDurationsPanelProps {
  durations: Record<string, number>;
}

export function AgentDurationsPanel({ durations }: AgentDurationsPanelProps) {
  const entries = Object.entries(durations).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0);

  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>各 Agent 耗时</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="pb-1">Agent</th>
              <th className="pb-1">耗时</th>
              <th className="pb-1">占比</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([name, ms]) => (
              <tr key={name} className="border-t border-border">
                <td className="py-1 pr-4">{name}</td>
                <td className="py-1 pr-4">{(ms / 1000).toFixed(2)}s</td>
                <td className="py-1">
                  {total > 0 ? ((ms / total) * 100).toFixed(1) : '0'}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
