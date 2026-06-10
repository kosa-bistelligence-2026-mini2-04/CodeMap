const INPUT_COST_PER_MTOK = 3
const OUTPUT_COST_PER_MTOK = 15

interface TokenUsageCardProps {
  inputTokens: number
  outputTokens: number
}

export function TokenUsageCard({ inputTokens, outputTokens }: TokenUsageCardProps) {
  const totalTokens = inputTokens + outputTokens
  const estimatedCost =
    (inputTokens / 1_000_000) * INPUT_COST_PER_MTOK +
    (outputTokens / 1_000_000) * OUTPUT_COST_PER_MTOK

  const formattedCost = estimatedCost < 0.01 ? '< $0.01' : `$${estimatedCost.toFixed(3)}`

  return (
    <div className="flex items-center gap-4 text-xs text-muted-foreground px-1">
      <TokenStat label="Input" value={inputTokens.toLocaleString()} unit="tokens" />
      <span className="text-border">·</span>
      <TokenStat label="Output" value={outputTokens.toLocaleString()} unit="tokens" />
      <span className="text-border">·</span>
      <TokenStat label="Total" value={totalTokens.toLocaleString()} unit="tokens" />
      <span className="text-border">·</span>
      <span className="text-muted-foreground">
        Est. cost <span className="font-medium text-foreground">{formattedCost}</span>
      </span>
    </div>
  )
}

function TokenStat({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <span>
      {label} <span className="font-medium text-foreground">{value}</span> <span>{unit}</span>
    </span>
  )
}
