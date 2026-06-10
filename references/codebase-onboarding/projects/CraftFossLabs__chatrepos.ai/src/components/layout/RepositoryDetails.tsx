"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import { MermaidDiagram } from "@/components/ui/mermaid-diagram";
import { useAnalysisStore } from "@/lib/store";

export function RepositoryDetails() {
  const { isAnalysisComplete, detailedSummary, workflowDiagram, analysisData } =
    useAnalysisStore();

  // Debug information
  console.log("RepositoryDetails - Rendering");
  console.log("isAnalysisComplete:", isAnalysisComplete);
  console.log("detailedSummary length:", detailedSummary?.length || 0);
  console.log("workflowDiagram length:", workflowDiagram?.length || 0);
  console.log("analysisData:", analysisData);

  if (!isAnalysisComplete) {
    return null;
  }

  return (
    <div className="flex flex-col h-full space-y-6">
      {detailedSummary && (
        <Card className="p-6 border-primary/20">
          <h2 className="text-xl font-bold mb-4 text-gradient">
            Detailed Analysis
          </h2>
          <div className="prose dark:prose-invert max-w-none">
            {detailedSummary.split("\n").map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        </Card>
      )}

      {workflowDiagram && (
        <div className="flex-1 min-h-[100vh] mt-2">
          <MermaidDiagram
            diagramDefinition={workflowDiagram}
            title="Repository Workflow Diagram"
          />
        </div>
      )}
    </div>
  );
}
