import React from "react";
import Image from "next/image";

export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground">
      <Image 
        src="/thinking-animation.svg" 
        alt="AI is thinking" 
        width={40} 
        height={40} 
        className="animate-pulse"
      />
      <span>AI is thinking...</span>
    </div>
  );
}
