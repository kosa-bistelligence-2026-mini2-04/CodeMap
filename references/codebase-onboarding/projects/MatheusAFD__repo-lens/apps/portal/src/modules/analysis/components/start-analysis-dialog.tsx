import {
  RECOMMENDED_SECTIONS,
  SECTION_META,
  SELECTABLE_SECTIONS,
} from '@/common/constants/analysis-sections'
import type { AnalysisSectionType } from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { Button } from '@repo/ui/components/button'
import { Checkbox } from '@repo/ui/components/checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@repo/ui/components/dialog'
import { Label } from '@repo/ui/components/label'
import { Textarea } from '@repo/ui/components/textarea'
import { useState } from 'react'
import type { StartAnalysisFormRequest } from '../schemas/start-analysis.schema'

interface StartAnalysisDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (request: StartAnalysisFormRequest) => void
  isStarting: boolean
}

export function StartAnalysisDialog({
  open,
  onOpenChange,
  onConfirm,
  isStarting,
}: StartAnalysisDialogProps) {
  const [selectedSections, setSelectedSections] = useState<Set<AnalysisSectionType>>(
    new Set(RECOMMENDED_SECTIONS),
  )
  const [customContext, setCustomContext] = useState('')

  function toggleSection(section: AnalysisSectionType) {
    setSelectedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  function handleConfirm() {
    const sections = SELECTABLE_SECTIONS.filter((s) => selectedSections.has(s))
    onConfirm({
      sections,
      customContext: customContext.trim() || undefined,
    })
  }

  const canSubmit = selectedSections.size > 0 && !isStarting

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Configure Analysis</DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="space-y-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Sections to generate
            </p>
            <div className="space-y-2">
              {SELECTABLE_SECTIONS.map((section) => {
                const meta = SECTION_META[section]
                const isRecommended = RECOMMENDED_SECTIONS.includes(section)
                const checked = selectedSections.has(section)
                return (
                  <div
                    key={section}
                    className="flex items-start gap-3 rounded-lg border border-border/50 px-3 py-2.5 hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => toggleSection(section)}
                    onKeyDown={(e) => e.key === 'Enter' && toggleSection(section)}
                  >
                    <Checkbox
                      id={section}
                      checked={checked}
                      onCheckedChange={() => toggleSection(section)}
                      onClick={(e) => e.stopPropagation()}
                      className="mt-0.5"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={section} className="text-sm font-medium cursor-pointer">
                          {meta.label}
                        </Label>
                        {isRecommended && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            Recommended
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{meta.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
            {selectedSections.size === 0 && (
              <p className="text-xs text-destructive">Select at least one section.</p>
            )}
          </div>

          <div className="space-y-2">
            <Label
              htmlFor="custom-context"
              className="text-xs font-medium text-muted-foreground uppercase tracking-wide"
            >
              Additional context (optional)
            </Label>
            <Textarea
              id="custom-context"
              value={customContext}
              onChange={(e) => setCustomContext(e.target.value)}
              placeholder="e.g. This is a B2B SaaS focused on LGPD compliance. Prioritize security findings."
              className="text-sm resize-none"
              rows={3}
              maxLength={500}
            />
            <p className="text-xs text-muted-foreground text-right">{customContext.length}/500</p>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isStarting}
          >
            Cancel
          </Button>
          <Button size="sm" onClick={handleConfirm} disabled={!canSubmit}>
            {isStarting ? 'Starting…' : 'Start Analysis'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
