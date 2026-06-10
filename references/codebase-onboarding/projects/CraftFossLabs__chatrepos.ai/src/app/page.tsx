"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/layout/Header";
import { RepositoryAnalyzer } from "@/components/layout/RepositoryAnalyzer";
import { RepositoryDetails } from "@/components/layout/RepositoryDetails";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { useAnalysisStore } from "@/lib/store";
import { Toaster } from "sonner";

export default function Home() {
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const { isAnalysisComplete } = useAnalysisStore();

  // Initialize theme based on system preference
  useEffect(() => {
    // Check for system preference
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)"
    ).matches;
    setIsDarkTheme(prefersDark);

    // Apply theme
    document.documentElement.classList.toggle("dark", prefersDark);
  }, []);

  // Toggle theme function
  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
    document.documentElement.classList.toggle("dark");
  };

  return (
    <div className="flex flex-col h-screen bg-white text-foreground overflow-hidden">
      <Toaster position="top-center" />
      <Header toggleTheme={toggleTheme} isDarkTheme={isDarkTheme} />

      {!isAnalysisComplete ? (
        <main className="flex-1 container mx-auto px-4 py-6 overflow-auto">
          <div className="max-w-3xl mx-auto w-full">
            <RepositoryAnalyzer />
          </div>
        </main>
      ) : (
        <div className="flex flex-col flex-1 h-full overflow-auto">
          {/* Repository Details with Workflow Diagram - Fixed height with inner scroll */}
          <div className="container mx-auto">
            <RepositoryDetails />
          </div>

          {/* Chat Interface - Fixed at bottom */}
          <div className="bg-background">
            <div className="container mx-auto">
              <ChatInterface />
            </div>
          </div>
        </div>
      )}

      <footer className="py-3 border-t">
        <div className="container mx-auto px-4 text-center text-sm text-black">
          <p className="">
            GitRepos.chat - Powered by
            <a
              href="https://craftfosslabs.com"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-1 font-bold text-gradient hover:text-accent transition-colors"
            >
              CraftFossLabs
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
