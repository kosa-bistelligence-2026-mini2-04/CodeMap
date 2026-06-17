"use client";

export function Footer() {
  return (
    <footer className="w-full border-t border-neutral-100 bg-white py-6">
      <div className="mx-auto max-w-7xl px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-[10px] text-neutral-400 font-medium">
        <div>
          &copy; {new Date().getFullYear()} CodeMap AI. All rights reserved.
        </div>
        <div className="flex gap-4">
          <a href="#" className="hover:text-neutral-900 transition-colors">
            Privacy Policy
          </a>
          <a href="#" className="hover:text-neutral-900 transition-colors">
            Terms of Service
          </a>
          <a href="#" className="hover:text-neutral-900 transition-colors">
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}
