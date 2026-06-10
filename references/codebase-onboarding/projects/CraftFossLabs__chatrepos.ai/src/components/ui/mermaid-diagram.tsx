/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Card } from "./card";
import { useAnalysisStore } from "@/lib/store";

interface MermaidDiagramProps {
  diagramDefinition: string;
  title?: string;
}

export function MermaidDiagram({
  diagramDefinition,
  title,
}: MermaidDiagramProps) {
  const diagramRef = useRef<HTMLDivElement>(null);
  const [renderMode, setRenderMode] = useState<"mermaid" | "fallback">("mermaid");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [diagramSvg, setDiagramSvg] = useState<string>("");

  // Get repository data from the store
  const { analysisData } = useAnalysisStore();

  // Process the diagram definition to ensure it's valid - first pass of cleanup
  const processDefinition = useCallback((definition: string): string => {
    // If definition is empty or undefined, return a minimal valid diagram
    if (!definition || definition.trim() === "") {
      return "graph TD\n    A[Empty] --> B[Diagram]";
    }
    
    // Make sure the diagram definition starts with a valid diagram type
    let processed = definition.trim();
    
    // Normalize line endings
    processed = processed.replace(/\r\n/g, "\n");
    
    // Remove any duplicate graph/flowchart declarations
    processed = processed.replace(/(?:graph|flowchart)\s+(?:TD|LR|RL|BT)\s*\n\s*(?:graph|flowchart)\s+(?:TD|LR|RL|BT)/g, (match) => {
      // Keep only the first declaration
      const firstDeclaration = match.split("\n")[0];
      return firstDeclaration;
    });
    
    // Fix common syntax errors
    // Replace invalid arrows
    processed = processed.replace(/--[^>]>/g, "-->");
    processed = processed.replace(/==[^>]>/g, "==>");
    
    // Fix incomplete arrow statements (arrows without target nodes)
    processed = processed.replace(/-->\s*(?:;|$)/gm, "--> Unknown");
    processed = processed.replace(/==>\s*(?:;|$)/gm, "==> Unknown");
    processed = processed.replace(/-.->\s*(?:;|$)/gm, "-.-> Unknown");
    processed = processed.replace(/--\s*(?:;|$)/gm, "--> Unknown");
    processed = processed.replace(/==\s*(?:;|$)/gm, "==> Unknown");
    processed = processed.replace(/-\.\s*(?:;|$)/gm, "-.-> Unknown");
    
    // Fix repeated node definitions with incomplete arrows
    // This pattern matches cases like "A[Label] A --" where a node is defined and then immediately used
    processed = processed.replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+--(?!>)/gm, "$1 --> Unknown");
    processed = processed.replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+==(?!>)/gm, "$1 ==> Unknown");
    processed = processed.replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+-\.(?!>)/gm, "$1 -.-> Unknown");
    
    // Fix node references without proper definition
    // First, extract all defined nodes
    const nodeDefRegex = /\b([A-Za-z0-9_-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})/g;
    const definedNodes = new Set<string>();
    let match;
    while ((match = nodeDefRegex.exec(processed)) !== null) {
      definedNodes.add(match[1]);
    }
    
    // Then, find node references in connections that don't have definitions
    const lines = processed.split("\n");
    const processedLines = lines.map(line => {
      // Skip if it's a comment or diagram type declaration
      if (line.trim().startsWith("%") || 
          line.trim().startsWith("graph") || 
          line.trim().startsWith("flowchart") ||
          line.trim().startsWith("subgraph") ||
          line.trim().startsWith("end")) {
        return line;
      }
      
      // Look for connection patterns
      const connRegex = /\b([A-Za-z0-9_-]+)\s*(?:-->|==>|-.->|--o|--x|\|>|<\||~~~|---|===)/g;
      let connMatch;
      while ((connMatch = connRegex.exec(line)) !== null) {
        const nodeId = connMatch[1];
        if (!definedNodes.has(nodeId) && !line.includes(`${nodeId}[`) && !line.includes(`${nodeId}(`) && !line.includes(`${nodeId}{`)) {
          // Add node definition before the connection
          line = line.replace(new RegExp(`\\b${nodeId}\\b(?!\\s*(?:\\[|\\(|\\{))`), `${nodeId}[${nodeId}]`);
        }
      }
      
      return line;
    });
    
    processed = processedLines.join("\n");
    
    // Remove trailing semicolons
    processed = processed.replace(/;\s*$/gm, "");
    
    // Ensure there's a valid diagram type at the start
    if (!processed.trim().startsWith("graph") && !processed.trim().startsWith("flowchart")) {
      processed = "graph TD\n" + processed;
    }
    
    return processed;
  }, []);

  // Validate and fix diagram to ensure it's error-free
  const validateAndFixDiagram = useCallback((diagram: string): string => {
    if (!diagram || diagram.trim() === "") {
      return "graph TD\n    A[Empty] --> B[Diagram]";
    }

    try {
      // Split the diagram into lines
      const lines = diagram.split("\n");
      const validatedLines: string[] = [];
      const definedNodes = new Set<string>();
      const referencedNodes = new Set<string>();
      let hasValidConnection = false;

      // First pass: collect all defined nodes
      lines.forEach(line => {
        const trimmedLine = line.trim();
        
        // Skip comments and diagram type declarations
        if (trimmedLine.startsWith("%") || 
            trimmedLine.startsWith("graph") || 
            trimmedLine.startsWith("flowchart") ||
            trimmedLine.startsWith("subgraph") ||
            trimmedLine.startsWith("end")) {
          return;
        }
        
        // Extract node definitions
        const nodeDefRegex = /\b([A-Za-z0-9_-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})/g;
        let match;
        while ((match = nodeDefRegex.exec(trimmedLine)) !== null) {
          definedNodes.add(match[1]);
        }
      });

      // Second pass: validate each line and fix issues
      lines.forEach(line => {
        const trimmedLine = line.trim();
        
        // Keep diagram type declarations, comments, and subgraph markers as is
        if (trimmedLine.startsWith("graph") || 
            trimmedLine.startsWith("flowchart") ||
            trimmedLine.startsWith("%") ||
            trimmedLine.startsWith("subgraph") ||
            trimmedLine.startsWith("end")) {
          validatedLines.push(line);
          return;
        }
        
        // Check for connection patterns
        const connRegex = /\b([A-Za-z0-9_-]+)\s*(?:-->|==>|-.->|--o|--x|\|>|<\||~~~|---|===)\s*([A-Za-z0-9_-]+)/g;
        let connMatch;
        const modifiedLine = line;
        let hasConnection = false;
        
        while ((connMatch = connRegex.exec(trimmedLine)) !== null) {
          const fromNode = connMatch[1];
          const toNode = connMatch[2];
          
          referencedNodes.add(fromNode);
          referencedNodes.add(toNode);
          
          // If either node isn't defined, add a definition
          if (!definedNodes.has(fromNode)) {
            definedNodes.add(fromNode);
            validatedLines.push(`    ${fromNode}[${fromNode}]`);
          }
          
          if (!definedNodes.has(toNode)) {
            definedNodes.add(toNode);
            validatedLines.push(`    ${toNode}[${toNode}]`);
          }
          
          hasConnection = true;
          hasValidConnection = true;
        }
        
        // If the line has a valid connection, add it
        if (hasConnection) {
          validatedLines.push(modifiedLine);
        } else if (trimmedLine.length > 0) {
          // This line has content but no valid connection
          // Check if it's a node definition
          const nodeDefRegex = /\b([A-Za-z0-9_-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})/g;
          if (nodeDefRegex.test(trimmedLine)) {
            validatedLines.push(modifiedLine);
          }
          // Otherwise, it might be an invalid line, so we skip it
        }
      });

      // If there are no valid connections, create at least one
      if (!hasValidConnection && definedNodes.size > 0) {
        const nodeArray = Array.from(definedNodes);
        if (nodeArray.length >= 2) {
          validatedLines.push(`    ${nodeArray[0]} --> ${nodeArray[1]}`);
        } else if (nodeArray.length === 1) {
          validatedLines.push(`    ${nodeArray[0]} --> Unknown`);
          validatedLines.push(`    Unknown[Unknown]`);
        }
      }

      // If no nodes were defined at all, create a minimal valid diagram
      if (definedNodes.size === 0) {
        return "graph TD\n    A[Repository] --> B[Components]";
      }

      // Reconstruct the diagram with the validated lines
      let validatedDiagram = lines.filter(line => 
        line.trim().startsWith("graph") || 
        line.trim().startsWith("flowchart")
      ).join("\n");

      // If no diagram type declaration was found, add one
      if (!validatedDiagram) {
        validatedDiagram = "graph TD";
      }

      // Add all the validated lines
      validatedDiagram += "\n" + validatedLines.join("\n");
      
      return validatedDiagram;
    } catch (error) {
      console.error("Error in validateAndFixDiagram:", error);
      return "graph TD\n    A[Error] --> B[Occurred]\n    B --> C[Fallback]";
    }
  }, []);

  // Create a fallback diagram when the original fails to render
  const createFallbackDiagram = useCallback((originalDiagram: string): string => {
    if (!originalDiagram || originalDiagram.trim() === "") {
      return "graph TD\n    A[Empty] --> B[Diagram]";
    }

    try {
      // First, clean up any syntax issues that might cause parsing errors
      const cleanedDiagram = originalDiagram
        // Fix incomplete arrows
        .replace(/-->\s*(?:;|$)/gm, "--> Unknown")
        .replace(/==>\s*(?:;|$)/gm, "==> Unknown")
        .replace(/-.->\s*(?:;|$)/gm, "-.-> Unknown")
        .replace(/--\s*(?:;|$)/gm, "--> Unknown")
        .replace(/==\s*(?:;|$)/gm, "==> Unknown")
        .replace(/-\.\s*(?:;|$)/gm, "-.-> Unknown")
        // Fix repeated node definitions
        .replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+--(?!>)/gm, "$1 --> Unknown")
        .replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+==(?!>)/gm, "$1 ==> Unknown")
        .replace(/([A-Za-z0-9_-]+(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))\s+\1\s+-\.(?!>)/gm, "$1 -.-> Unknown")
        // Remove trailing semicolons
        .replace(/;\s*$/gm, "");
      
      // Fix the connection pattern to avoid duplicate arrow types
      const connectionPattern =
        /([A-Za-z0-9_-]+)\s*(?:-->|==>|-.->|--o|--x|\|>|<\||~~~|---|===|~~~>|--\*|==\*)\s*([A-Za-z0-9_-]+)/g;

      const lines = cleanedDiagram.split("\n");
      const nodes = new Set<string>();
      const connections: { from: string; to: string }[] = [];
      const nodeLabels: Record<string, string> = {};

      // Extract nodes and connections
      lines.forEach((line) => {
        // Skip comment lines
        if (line.trim().startsWith("%")) return;
        
        // Extract node IDs and their labels
        const nodeDefRegex = /\b([A-Za-z0-9_-]+)\s*(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\})/g;
        let nodeMatch;
        while ((nodeMatch = nodeDefRegex.exec(line)) !== null) {
          const nodeId = nodeMatch[1].trim();
          // Get the label from whichever bracket type was used
          const label = nodeMatch[2] || nodeMatch[3] || nodeMatch[4] || nodeId;
          
          if (nodeId && !nodeId.includes(" ") && nodeId.length > 0) {
            nodes.add(nodeId);
            nodeLabels[nodeId] = label;
          }
        }

        // Extract connections
        let connectionMatch;
        // Normalize whitespace and fix any incomplete arrow statements
        const connectionText = line.replace(/\s+/g, " ")
          .replace(/-->\s*(?:;|$)/g, "--> Unknown")
          .replace(/==>\s*(?:;|$)/g, "==> Unknown")
          .replace(/-.->\s*(?:;|$)/g, "-.-> Unknown")
          .replace(/--\s*(?:;|$)/g, "--> Unknown")
          .replace(/==\s*(?:;|$)/g, "==> Unknown")
          .replace(/-\.\s*(?:;|$)/g, "-.-> Unknown");
        
        while ((connectionMatch = connectionPattern.exec(connectionText)) !== null) {
          const from = connectionMatch[1].trim();
          const to = connectionMatch[2].trim();
          
          // Only add valid connections
          if (from && to && from.length > 0 && to.length > 0) {
            connections.push({ from, to });
            // Also add the nodes if they weren't already detected
            nodes.add(from);
            nodes.add(to);
          }
        }
      });

      // Create a simplified diagram
      let fallbackDiagram = "graph TD\n";

      // Add node definitions
      nodes.forEach((node) => {
        // Use the extracted label if available, otherwise use the node ID
        const label = nodeLabels[node] || node;
        fallbackDiagram += `    ${node}[${label}]\n`;
      });

      // Add connections
      connections.forEach((conn) => {
        fallbackDiagram += `    ${conn.from} --> ${conn.to}\n`;
      });

      // If no nodes were found, create a default diagram
      if (nodes.size === 0) {
        fallbackDiagram =
          "graph TD\n    A[Repository] --> B[Components]\n    B --> C[Features]";
      }

      // Final safety check - make sure there are no incomplete arrows or syntax issues
      fallbackDiagram = validateAndFixDiagram(fallbackDiagram);
      
      return fallbackDiagram;
    } catch (error) {
      console.error("Error creating fallback diagram:", error);
      // Return a guaranteed-to-work minimal diagram
      return "graph TD\n    A[Repository] --> B[Components]";
    }
  }, [validateAndFixDiagram]);
  
  // Analyze and ensure a diagram is 100% error-free
  const ensurePerfectDiagram = useCallback((diagram: string): string => {
    if (!diagram || diagram.trim() === "") {
      return "graph TD\n    A[Empty] --> B[Diagram]";
    }
    
    try {
      // First, apply the initial cleaning process
      let perfectDiagram = processDefinition(diagram);
      
      // Then validate and fix any structural issues
      perfectDiagram = validateAndFixDiagram(perfectDiagram);
      
      // Advanced error checking and fixing
      
      // 1. Ensure there's exactly one diagram type declaration at the beginning
      const diagramTypes = ["graph", "flowchart", "sequenceDiagram", "classDiagram", 
                          "stateDiagram", "erDiagram", "gantt", "pie", "journey"];
      
      // Check if there's a valid diagram type
      const hasValidType = diagramTypes.some(type => 
        perfectDiagram.trim().startsWith(type));
      
      if (!hasValidType) {
        perfectDiagram = "graph TD\n" + perfectDiagram;
      }
      
      // 2. Fix direction declarations
      const validDirections = ["TB", "TD", "BT", "RL", "LR"];
      const directionMatch = perfectDiagram.match(/^(graph|flowchart)\s+([A-Z]{2})/i);
      
      if (directionMatch && !validDirections.includes(directionMatch[2].toUpperCase())) {
        // Replace invalid direction with TD
        perfectDiagram = perfectDiagram.replace(
          /^(graph|flowchart)\s+([A-Z]{2})/i, 
          `$1 TD`
        );
      }
      
      // 3. Handle class definitions and styling
      const classDefRegex = /classDef\s+([A-Za-z0-9_-]+)\s+([^;\n]+)/g;
      let classMatch;
      while ((classMatch = classDefRegex.exec(perfectDiagram)) !== null) {
        const className = classMatch[1];
        const styleText = classMatch[2];
        
        // Ensure style text is properly formatted
        if (!styleText.includes(':') && !styleText.startsWith('{')) {
          // Add proper formatting to the style
          const fixedStyle = `fill:#f9f9f9,stroke:#666,stroke-width:1px`;
          perfectDiagram = perfectDiagram.replace(
            `classDef ${className} ${styleText}`,
            `classDef ${className} ${fixedStyle}`
          );
        }
      }
      
      // 4. Check for and fix incomplete subgraphs
      const subgraphCount = (perfectDiagram.match(/subgraph/g) || []).length;
      const endCount = (perfectDiagram.match(/\bend\b/g) || []).length;
      
      if (subgraphCount > endCount) {
        // Add missing 'end' statements
        perfectDiagram += '\n' + 'end'.repeat(subgraphCount - endCount);
      }
      
      // 5. Ensure all node references exist
      const nodeDefRegex = /\b([A-Za-z0-9_-]+)\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})/g;
      const definedNodes = new Set<string>();
      
      // Collect all defined nodes
      let nodeMatch;
      while ((nodeMatch = nodeDefRegex.exec(perfectDiagram)) !== null) {
        definedNodes.add(nodeMatch[1]);
      }
      
      // Check for references to undefined nodes in connections
      const connRegex = /\b([A-Za-z0-9_-]+)\s*(?:-->|==>|-.->|--o|--x|\|>|<\||~~~|---|===)\s*([A-Za-z0-9_-]+)/g;
      const referencedNodes = new Set<string>();
      let connMatch;
      
      while ((connMatch = connRegex.exec(perfectDiagram)) !== null) {
        referencedNodes.add(connMatch[1]);
        referencedNodes.add(connMatch[2]);
      }
      
      // Add definitions for referenced but undefined nodes
      const lines = perfectDiagram.split('\n');
      for (const node of referencedNodes) {
        if (!definedNodes.has(node) && node !== 'Unknown') {
          // Find a good place to insert the node definition
          // Look for the first non-header line
          let insertIndex = 0;
          for (let i = 0; i < lines.length; i++) {
            if (!lines[i].trim().startsWith('graph') && 
                !lines[i].trim().startsWith('flowchart') &&
                !lines[i].trim().startsWith('%')) {
              insertIndex = i;
              break;
            }
          }
          
          // Insert the node definition
          lines.splice(insertIndex, 0, `    ${node}[${node}]`);
          definedNodes.add(node);
        }
      }
      
      perfectDiagram = lines.join('\n');
      
      return perfectDiagram;
    } catch (error) {
      console.error("Error in ensurePerfectDiagram:", error);
      // If all else fails, return a simple valid diagram
      return "graph TD\n    A[Error] --> B[In] --> C[Processing]";
    }
  }, [processDefinition, validateAndFixDiagram]);

  // Render the diagram
  const renderDiagram = useCallback(async () => {
    if (!diagramDefinition) {
      setDiagramSvg("");
      return;
    }

    try {
      const { svg } = await mermaid.render(
        `mermaid-${Date.now()}`,
        processDefinition(diagramDefinition)
      );
      setDiagramSvg(svg);
      setRenderMode("mermaid");
      setErrorMessage("");
    } catch (error) {
      console.error("Initial diagram render failed:", error);
      try {
        // Try a simplified version
        const sanitizedDefinition = diagramDefinition.replace(/[^a-zA-Z0-9\s\[\]\-_>]/g, '');
        const { svg: sanitizedSvg } = await mermaid.render(
          `sanitized-${Date.now()}`,
          sanitizedDefinition
        );
        setDiagramSvg(sanitizedSvg);
        setRenderMode("fallback");
        setErrorMessage("Diagram was simplified due to syntax issues");
      } catch (sanitizedError) {
        // Create a minimal fallback diagram
        const minimalDiagram = "graph TD\n    A[Error] --> B[Rendering Failed]";
        try {
          const { svg: minimalSvg } = await mermaid.render(
            `minimal-${Date.now()}`,
            minimalDiagram
          );
          setDiagramSvg(minimalSvg);
          setRenderMode("fallback");
          setErrorMessage("Failed to render diagram due to syntax errors");
        } catch (minimalError) {
          // Create an SVG manually as absolute last resort
          const manualSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 200 100">
            <rect width="100%" height="100%" fill="#f5f5f5"/>
            <text x="50%" y="50%" font-family="Arial" font-size="14" text-anchor="middle">Diagram Rendering Failed</text>
          </svg>`;
          setDiagramSvg(manualSvg);
          setRenderMode("fallback");
          setErrorMessage("Failed to render diagram");
        }
      }
    }
  }, [diagramDefinition, processDefinition]);

  // Trigger render when diagram changes
  useEffect(() => {
    renderDiagram();
  }, [renderDiagram]);

  // Update the DOM when SVG changes
  useEffect(() => {
    if (diagramRef.current && diagramSvg) {
      diagramRef.current.innerHTML = diagramSvg;
    }
  }, [diagramSvg]);

  return (
    <Card className="flex flex-col h-full">
      {title && (
        <div className="px-4 py-3 border-b font-medium">{title}</div>
      )}
      {renderMode === "fallback" && errorMessage && (
        <div className="px-4 py-2 text-sm text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-400">
          <p>
            <strong>Note:</strong> {errorMessage}
          </p>
        </div>
      )}
      <div className="flex-1 p-4 overflow-auto">
        <div
          ref={diagramRef}
          className="mermaid-diagram w-full h-full flex items-center justify-center"
          dangerouslySetInnerHTML={{ __html: diagramSvg }}
        />
      </div>
    </Card>
  );
}
