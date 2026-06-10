import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useAnalysisStore } from "@/lib/store";
import { isValidGitHubUrl } from "@/lib/utils";
import { toast } from "sonner";

export function RepositoryAnalyzer() {
  const {
    setRepoUrl,
    setIsValidating,
    setIsAnalyzing,
    setAnalysisData,
    setAiSummary,
    setDetailedSummary,
    setWorkflowDiagram,
    setIsAnalysisComplete,
    setError,
    resetState,
  } = useAnalysisStore();

  const [inputUrl, setInputUrl] = useState("");
  const [progress, setProgress] = useState(0);
  const [analysisStep, setAnalysisStep] = useState("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputUrl(e.target.value);
  };

  const validateAndAnalyzeRepo = async () => {
    // Reset previous state
    resetState();
    setRepoUrl(inputUrl);
    
    // Basic URL validation
    if (!isValidGitHubUrl(inputUrl)) {
      toast.error("Please enter a valid GitHub repository URL");
      return;
    }

    try {
      // Start validation
      setIsValidating(true);
      setAnalysisStep("Validating repository URL...");
      setProgress(10);

      // Validate repository
      const validateResponse = await fetch("/api/validate-repo", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: inputUrl }),
      });

      if (!validateResponse.ok) {
        const errorData = await validateResponse.json();
        throw new Error(errorData.error || "Failed to validate repository");
      }

      // Start analysis
      setIsValidating(false);
      setIsAnalyzing(true);
      setAnalysisStep("Fetching repository data...");
      setProgress(30);

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });

        setAnalysisStep((prev) => {
          const steps = [
            "Fetching repository data...",
            "Analyzing code structure...",
            "Examining dependencies...",
            "Reviewing documentation...",
            "Generating AI insights...",
          ];
          const currentIndex = steps.indexOf(prev);
          return steps[Math.min(currentIndex + 1, steps.length - 1)];
        });
      }, 2000);

      // Analyze repository
      const analyzeResponse = await fetch("/api/analyze-repo", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: inputUrl }),
      });

      clearInterval(progressInterval);

      if (!analyzeResponse.ok) {
        const errorData = await analyzeResponse.json();
        throw new Error(errorData.error || "Failed to analyze repository");
      }

      // Process analysis results
      const analysisData = await analyzeResponse.json();
      
      // Log the analysis data to help debug
      console.log("Analysis data received:", analysisData);
      
      // Set the analysis data
      setAnalysisData({
        repoData: analysisData.repoData,
        repoContent: analysisData.repoContent,
      });
      
      // Make sure we have a valid summary
      const summary = analysisData.aiAnalysis?.summary || 
        "This repository appears to be a software project. I've analyzed its structure and code patterns.";
      
      console.log("Setting AI summary:", summary);
      setAiSummary(summary);
      
      // Set detailed summary if available
      const detailedSummary = analysisData.aiAnalysis?.detailedSummary || "";
      if (detailedSummary) {
        console.log("Setting detailed summary");
        setDetailedSummary(detailedSummary);
      }
      
      // Set workflow diagram if available
      const workflowDiagram = analysisData.aiAnalysis?.workflowDiagram || "";
      console.log("Workflow diagram from API:", workflowDiagram);
      console.log("Workflow diagram type:", typeof workflowDiagram);
      console.log("Workflow diagram length:", workflowDiagram?.length || 0);
      
      if (workflowDiagram) {
        console.log("Setting workflow diagram to store");
        setWorkflowDiagram(workflowDiagram);
      } else {
        console.log("No workflow diagram found in API response");
      }
      
      // Complete analysis
      setProgress(100);
      setAnalysisStep("Analysis complete!");
      setIsAnalyzing(false);
      
      // Set analysis complete after a small delay to ensure state updates
      setTimeout(() => {
        setIsAnalysisComplete(true);
        console.log("Analysis complete state set to true");
      }, 300);
      
      toast.success("Repository analysis complete!");
    } catch (error) {
      console.error("Error analyzing repository:", error);
      setError((error as Error).message);
      toast.error((error as Error).message || "Failed to analyze repository");
      setIsValidating(false);
      setIsAnalyzing(false);
      setProgress(0);
    }
  };

  return (
    <Card className="p-6 border-primary/20">
      <div className="space-y-6">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-gradient">GitHub Repository Analyzer</h2>
          <p className="text-muted-foreground">
            Enter a GitHub repository URL to analyze its structure and get AI-powered insights
          </p>
        </div>
        
        <div className="flex gap-2">
          <Input
            placeholder="Paste your public GitHub repository URL here..."
            value={inputUrl}
            onChange={handleInputChange}
            disabled={useAnalysisStore.getState().isAnalyzing}
            className="border-primary/50 focus:border-primary"
          />
          <Button 
            onClick={validateAndAnalyzeRepo}
            disabled={!inputUrl || useAnalysisStore.getState().isAnalyzing}
            className="bg-gradient-primary hover:opacity-90 transition-opacity"
          >
            Analyze
          </Button>
        </div>
        
        {(useAnalysisStore.getState().isValidating || useAnalysisStore.getState().isAnalyzing) && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{analysisStep}</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="bg-secondary h-2" />
          </div>
        )}
      </div>
    </Card>
  );
}
