
import { Button } from "./ui/button";

export function NotFound() {
  function handleReturnHome() {
    window.location.href = "/";
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-center p-8">
      <h1 className="text-6xl font-bold mb-4 text-main">404</h1>
      <h2 className="text-2xl font-semibold mb-2">Page Not Found</h2>
      <p className="mb-6 text-lg text-foreground/70">Sorry, the page you are looking for does not exist or is not supported.</p>
      <Button className="px-6 py-3 bg-main text-white rounded-lg text-lg font-medium hover:bg-main/80 transition-colors" onClick={handleReturnHome}>Return Home</Button>
    </div>
  );
}