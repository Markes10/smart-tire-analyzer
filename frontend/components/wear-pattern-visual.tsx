"use client"

interface WearPatternVisualProps {
  pattern: "even" | "center" | "edge" | "one-side" | "cupping" | "feathering" | "patch"
  wearLevels: number[] // Array of 5 zones from left to right
}

const patternLabels: Record<WearPatternVisualProps["pattern"], string> = {
  "even": "Even Wear",
  "center": "Center Wear",
  "edge": "Edge Wear",
  "one-side": "One-Side Wear",
  "cupping": "Cupping",
  "feathering": "Feathering",
  "patch": "Patch Wear",
}

const patternDescriptions: Record<WearPatternVisualProps["pattern"], string> = {
  "even": "Normal wear pattern indicating proper alignment and inflation.",
  "center": "May indicate over-inflation. Reduce tire pressure to recommended levels.",
  "edge": "May indicate under-inflation. Increase tire pressure to recommended levels.",
  "one-side": "Indicates alignment issues. Have your alignment checked.",
  "cupping": "Caused by worn suspension components. Have suspension inspected.",
  "feathering": "Often caused by toe misalignment. Have alignment checked.",
  "patch": "Indicates irregular wear from flat spots or damaged areas.",
}

export function WearPatternVisual({ pattern, wearLevels }: WearPatternVisualProps) {
  const getWearColor = (level: number) => {
    if (level >= 80) return "bg-success"
    if (level >= 60) return "bg-chart-2"
    if (level >= 40) return "bg-warning"
    return "bg-critical"
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-foreground">{patternLabels[pattern]}</h4>
      </div>
      
      {/* Tire visualization */}
      <div className="relative rounded-2xl border border-border/50 bg-muted/30 p-6">
        <div className="flex items-end justify-center gap-1">
          {wearLevels.map((level, index) => (
            <div key={index} className="flex flex-col items-center gap-2">
              <div 
                className={`w-8 rounded-t transition-all ${getWearColor(level)}`}
                style={{ height: `${level * 0.8}px` }}
              />
              <div className="h-4 w-8 rounded-b bg-muted-foreground/30" />
              <span className="text-xs text-muted-foreground">{level}%</span>
            </div>
          ))}
        </div>
        
        {/* Zone labels */}
        <div className="mt-4 flex justify-between text-xs text-muted-foreground">
          <span>Outer</span>
          <span>Center</span>
          <span>Outer</span>
        </div>
      </div>

      <p className="text-sm leading-relaxed text-muted-foreground">
        {patternDescriptions[pattern]}
      </p>
    </div>
  )
}
