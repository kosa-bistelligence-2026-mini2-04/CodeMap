replacement = """              - Example 1 (Linear Pipeline):
```svg
<svg viewBox="0 0 820 220" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <marker id="a1" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#71717a"/>
    </marker>
    <filter id="glow1" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <text x="20" y="32" font-size="16" font-weight="600" fill="#e4e4e7">CI/CD Deployment Pipeline</text>
  
  <rect class="node" x="20" y="70" width="160" height="52" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="100" y="101" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">1. Checkout</text>
  
  <rect class="node" x="230" y="70" width="160" height="52" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="310" y="101" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">2. Test &amp; Build</text>
  
  <rect class="node" x="440" y="70" width="160" height="52" rx="8" fill="#18181b" stroke="#34d399" stroke-width="2"/>
  <text x="520" y="101" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">3. Deploy Prod</text>
  
  <path class="edge" id="route-1" d="M180 96 L220 96" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a1)"/>
  <path class="edge" id="route-2" d="M390 96 L430 96" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a1)"/>
  
  <circle class="bead" r="4" fill="#60a5fa" filter="url(#glow1)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-1"/></animateMotion>
  </circle>
  <circle class="bead" r="4" fill="#60a5fa" filter="url(#glow1)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-2"/></animateMotion>
  </circle>
  
  <g class="legend">
    <text x="20" y="180" font-size="12" fill="#a1a1aa">Legend: Blue glowing bead = active job progression</text>
  </g>
</svg>
```

              - Example 2 (Decision Branch):
```svg
<svg viewBox="0 0 860 280" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <marker id="a2" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#71717a"/>
    </marker>
    <filter id="glow2" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <text x="24" y="34" font-size="16" font-weight="600" fill="#e4e4e7">Authentication Flow</text>
  
  <rect class="node" x="40" y="90" width="160" height="56" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="120" y="118" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Login Request</text>
  
  <polygon class="node" points="320,86 390,118 320,150 250,118" fill="#18181b" stroke="#a78bfa" stroke-width="2"/>
  <text x="320" y="118" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Valid Token?</text>
  
  <rect class="node" x="510" y="46" width="160" height="56" rx="8" fill="#18181b" stroke="#34d399" stroke-width="2"/>
  <text x="590" y="74" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Access Granted</text>
  
  <rect class="node" x="510" y="146" width="160" height="56" rx="8" fill="#18181b" stroke="#f87171" stroke-width="2"/>
  <text x="590" y="174" font-size="14" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Access Denied</text>
  
  <path class="edge" id="route-in" d="M200 118 L240 118" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a2)"/>
  <path class="edge" id="route-yes" d="M390 118 L460 118 L460 74 L500 74" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a2)"/>
  <text x="430" y="112" font-size="12" fill="#34d399" text-anchor="middle">Yes</text>
  
  <path class="edge" id="route-no" d="M320 150 L320 174 L500 174" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a2)"/>
  <text x="340" y="168" font-size="12" fill="#f87171" text-anchor="middle">No</text>
  
  <circle class="bead" r="4" fill="#60a5fa" filter="url(#glow2)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-in"/></animateMotion>
  </circle>
  <circle class="bead" r="4" fill="#34d399" filter="url(#glow2)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-yes"/></animateMotion>
  </circle>
  <circle class="bead" r="4" fill="#f87171" filter="url(#glow2)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-no"/></animateMotion>
  </circle>
  
  <g class="legend">
    <text x="40" y="250" font-size="12" fill="#a1a1aa">Legend: Green = Success path, Red = Failure path</text>
  </g>
</svg>
```

              - Example 3 (Swimlane Workflow):
```svg
<svg viewBox="0 0 880 340" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <marker id="a3" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#71717a"/>
    </marker>
    <filter id="glow3" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <text x="20" y="30" font-size="16" font-weight="600" fill="#e4e4e7">Multi-Agent Request Processing</text>
  
  <rect class="lane" x="20" y="50" width="840" height="80" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="1" stroke-dasharray="4"/>
  <text x="36" y="94" font-size="14" font-weight="600" fill="#a78bfa">User Agent</text>
  
  <rect class="lane" x="20" y="140" width="840" height="80" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="1" stroke-dasharray="4"/>
  <text x="36" y="184" font-size="14" font-weight="600" fill="#60a5fa">Web App API</text>
  
  <rect class="lane" x="20" y="230" width="840" height="80" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="1" stroke-dasharray="4"/>
  <text x="36" y="274" font-size="14" font-weight="600" fill="#34d399">Data Worker</text>
  
  <rect class="node" x="180" y="65" width="140" height="46" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="250" y="88" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Submit Job</text>
  
  <rect class="node" x="400" y="155" width="140" height="46" rx="8" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="470" y="178" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Auth &amp; Route</text>
  
  <rect class="node" x="620" y="245" width="140" height="46" rx="8" fill="#18181b" stroke="#34d399" stroke-width="2"/>
  <text x="690" y="268" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Process Record</text>
  
  <path class="edge" id="route-swim-1" d="M320 88 L360 88 L360 178 L390 178" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a3)"/>
  <path class="edge" id="route-swim-2" d="M540 178 L580 178 L580 268 L610 268" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a3)"/>
  
  <circle class="bead" r="4" fill="#a78bfa" filter="url(#glow3)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-swim-1"/></animateMotion>
  </circle>
  <circle class="bead" r="4" fill="#60a5fa" filter="url(#glow3)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-swim-2"/></animateMotion>
  </circle>
  
  <g class="legend">
    <text x="20" y="330" font-size="12" fill="#a1a1aa">Legend: Dashed boxes = Context boundaries</text>
  </g>
</svg>
```

              - Example 4 (Layered Architecture):
```svg
<svg viewBox="0 0 860 340" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <marker id="a4" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#71717a"/>
    </marker>
    <filter id="glow4" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <text x="24" y="34" font-size="16" font-weight="600" fill="#e4e4e7">System Layer Architecture</text>
  
  <rect class="layer" x="20" y="60" width="820" height="70" rx="8" fill="#18181b" stroke="#60a5fa" stroke-width="1" stroke-dasharray="4"/>
  <text x="40" y="98" font-size="14" font-weight="600" fill="#60a5fa">Gateway / Edge</text>
  
  <rect class="layer" x="20" y="146" width="820" height="70" rx="8" fill="#18181b" stroke="#a78bfa" stroke-width="1" stroke-dasharray="4"/>
  <text x="40" y="184" font-size="14" font-weight="600" fill="#a78bfa">Microservices</text>
  
  <rect class="layer" x="20" y="232" width="820" height="70" rx="8" fill="#18181b" stroke="#34d399" stroke-width="1" stroke-dasharray="4"/>
  <text x="40" y="270" font-size="14" font-weight="600" fill="#34d399">Data stores</text>
  
  <rect class="node" x="240" y="75" width="160" height="40" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="320" y="95" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Load Balancer</text>
  
  <rect class="node" x="460" y="161" width="160" height="40" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="540" y="181" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">Auth Service</text>
  
  <rect class="node" x="660" y="247" width="160" height="40" rx="6" fill="#18181b" stroke="#3f3f46" stroke-width="2"/>
  <text x="740" y="267" font-size="13" fill="#e4e4e7" text-anchor="middle" dominant-baseline="middle">PostgreSQL</text>
  
  <path class="edge" id="route-stack-1" d="M400 95 L430 95 L430 181 L450 181" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a4)"/>
  <path class="edge" id="route-stack-2" d="M620 181 L640 181 L640 267 L650 267" stroke="#71717a" stroke-width="2" fill="none" marker-end="url(#a4)"/>
  
  <circle class="bead" r="4" fill="#fbbf24" filter="url(#glow4)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-stack-1"/></animateMotion>
  </circle>
  <circle class="bead" r="4" fill="#fbbf24" filter="url(#glow4)">
    <animateMotion dur="2.5s" repeatCount="indefinite"><mpath href="#route-stack-2"/></animateMotion>
  </circle>
  
  <g class="legend">
    <text x="24" y="326" font-size="12" fill="#a1a1aa">Legend: Layers indicate network boundaries</text>
  </g>
</svg>
```

              - Example 5 (Timeline with Milestones):
```svg
<svg viewBox="0 0 900 240" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <marker id="a5" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#71717a"/>
    </marker>
    <filter id="glow5" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>
  <text x="24" y="34" font-size="16" font-weight="600" fill="#e4e4e7">Event Processing Lifecycle</text>
  
  <path class="edge" id="route-time" d="M60 120 L820 120" stroke="#3f3f46" stroke-width="4" fill="none" marker-end="url(#a5)"/>
  
  <circle cx="160" cy="120" r="16" fill="#18181b" stroke="#60a5fa" stroke-width="3"/>
  <text x="160" y="156" font-size="14" fill="#60a5fa" text-anchor="middle">Ingest</text>
  <text x="160" y="176" font-size="12" fill="#a1a1aa" text-anchor="middle">Log captured</text>
  
  <circle cx="360" cy="120" r="16" fill="#18181b" stroke="#a78bfa" stroke-width="3"/>
  <text x="360" y="156" font-size="14" fill="#a78bfa" text-anchor="middle">Transform</text>
  <text x="360" y="176" font-size="12" fill="#a1a1aa" text-anchor="middle">Schema applied</text>
  
  <circle cx="560" cy="120" r="16" fill="#18181b" stroke="#fbbf24" stroke-width="3"/>
  <text x="560" y="156" font-size="14" fill="#fbbf24" text-anchor="middle">Enrich</text>
  <text x="560" y="176" font-size="12" fill="#a1a1aa" text-anchor="middle">Geo-lookup</text>
  
  <circle cx="760" cy="120" r="16" fill="#18181b" stroke="#34d399" stroke-width="3"/>
  <text x="760" y="156" font-size="14" fill="#34d399" text-anchor="middle">Sink</text>
  <text x="760" y="176" font-size="12" fill="#a1a1aa" text-anchor="middle">Saved to DL</text>
  
  <circle class="bead" r="5" fill="#e4e4e7" filter="url(#glow5)">
    <animateMotion dur="4s" repeatCount="indefinite"><mpath href="#route-time"/></animateMotion>
  </circle>
  
  <g class="legend">
    <text x="24" y="220" font-size="12" fill="#a1a1aa">Legend: Flow progresses left to right synchronously</text>
  </g>
</svg>
```"""

with open('src/lib/prompt-builder.ts', 'r') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '- Example 1 (Linear Pipeline):' in line:
        start_idx = i
    if '- Example 5 (Timeline with Milestones):' in line:
        for j in range(i+1, len(lines)):
            if lines[j].strip() == '```':
                end_idx = j
                break
        if end_idx != -1:
            break

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx] + [replacement + '\n'] + lines[end_idx+1:]
    with open('src/lib/prompt-builder.ts', 'w') as f:
        f.writelines(new_lines)
    print("Successfully replaced.")
else:
    print(f"Failed to find bounds. Start: {start_idx}, End: {end_idx}")

