class OnboardingGuide:
    """Agent responsible for writing user guidelines, walkthroughs, and setting up initial environments."""
    
    def __init__(self, model: str):
        self.model = model
        
    async def run(self, doc_layout: str) -> str:
        return "## How to get started..."
