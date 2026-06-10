import React from "react";
import { MoonIcon, SunIcon } from "@radix-ui/react-icons";
import { Button } from "@/components/ui/button";
import Image from "next/image";

interface HeaderProps {
  toggleTheme: () => void;
  isDarkTheme: boolean;
}

export function Header({ toggleTheme, isDarkTheme }: HeaderProps) {
  return (
    <header className="border-b border-border bg-gray-50">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <Image 
            src="/gitreposlogo-g.svg" 
            alt="GitRepos.chat Logo" 
            width={48} 
            height={48} 
            className="h-12 w-12" 
          />
          <h1 className="text-xl font-bold text-gradient">GitRepos.chat</h1>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label="Toggle theme"
          >
            {isDarkTheme ? (
              <SunIcon className="h-5 w-5" />
            ) : (
              <MoonIcon className="h-5 w-5" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
