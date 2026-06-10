#!/usr/bin/env python
"""CLI interface for CodeBase Intelligence RAG."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from typing import Optional

app = typer.Typer(
    name="codebase-rag",
    help="🧠 CodeBase Intelligence RAG - Chat with any codebase",
)
console = Console()

# Global state
_retriever = None
_generator = None
_reranker = None


def get_components():
    """Lazy load components."""
    global _retriever, _generator, _reranker
    
    if _retriever is None:
        from src.retrieval import HybridRetriever, LightweightReranker
        from src.generation import CodeGenerator
        
        _retriever = HybridRetriever()
        _generator = CodeGenerator()
        _reranker = LightweightReranker()
    
    return _retriever, _generator, _reranker


@app.command()
def ingest(
    repo_url: str = typer.Argument(..., help="GitHub repository URL"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to clone"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-clone"),
):
    """Ingest a GitHub repository into the RAG system."""
    from src.ingestion import GitHubLoader
    from src.chunking import ASTChunker
    
    with console.status("[bold green]Ingesting repository..."):
        # Load
        console.print(f"📦 Cloning [cyan]{repo_url}[/cyan]...")
        loader = GitHubLoader()
        files = loader.clone_repo(repo_url, branch=branch, force=force)
        
        console.print(f"📄 Found [green]{len(files)}[/green] files")
        
        # Chunk
        console.print("🧩 Chunking files...")
        chunker = ASTChunker()
        chunks = chunker.chunk_files(files)
        
        console.print(f"✂️ Created [green]{len(chunks)}[/green] chunks")
        
        # Index
        console.print("📊 Indexing chunks...")
        retriever, _, _ = get_components()
        retriever.index(chunks)
    
    console.print(Panel.fit(
        f"[bold green]✅ Successfully indexed![/bold green]\n\n"
        f"Files: {len(files)}\n"
        f"Chunks: {len(chunks)}\n\n"
        f"Run [cyan]codebase-rag query \"your question\"[/cyan] to search",
        title="Ingestion Complete",
    ))


@app.command()
def query(
    question: str = typer.Argument(..., help="Question about the codebase"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
    no_rerank: bool = typer.Option(False, "--no-rerank", help="Disable reranking"),
    show_sources: bool = typer.Option(True, "--sources/--no-sources", help="Show sources"),
):
    """Query the indexed codebase."""
    import time
    
    retriever, generator, reranker = get_components()
    
    with console.status("[bold blue]Searching..."):
        # Retrieve
        start = time.time()
        results = retriever.search(question, top_k=top_k * 2)
        
        if not results:
            console.print("[yellow]No results found. Try a different query.[/yellow]")
            return
        
        # Rerank
        if not no_rerank:
            results = reranker.rerank(question, results, top_k=top_k)
        else:
            results = results[:top_k]
        
        retrieval_time = time.time() - start
        
        # Generate
        start = time.time()
        answer = generator.generate(question, results)
        generation_time = time.time() - start
    
    # Display answer
    console.print()
    console.print(Panel(Markdown(answer), title="[bold]Answer[/bold]", border_style="green"))
    
    # Display sources
    if show_sources:
        table = Table(title="Sources", show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("File", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Name", style="yellow")
        table.add_column("Score", justify="right")
        
        for i, r in enumerate(results[:5], 1):
            meta = r.get("metadata", {})
            table.add_row(
                str(i),
                meta.get("file_path", "unknown"),
                meta.get("chunk_type", "code"),
                meta.get("name", "-"),
                f"{r.get('score', 0):.3f}",
            )
        
        console.print(table)
    
    # Timing
    console.print(f"\n[dim]⏱️ Retrieval: {retrieval_time*1000:.0f}ms | Generation: {generation_time*1000:.0f}ms[/dim]")


@app.command()
def chat():
    """Start interactive chat mode."""
    from prompt_toolkit import prompt
    from prompt_toolkit.history import FileHistory
    
    retriever, generator, reranker = get_components()
    
    console.print(Panel.fit(
        "[bold]🧠 CodeBase Intelligence RAG[/bold]\n\n"
        "Type your questions and press Enter.\n"
        "Type [cyan]exit[/cyan] or [cyan]quit[/cyan] to leave.\n"
        "Type [cyan]clear[/cyan] to clear the screen.",
        title="Interactive Chat",
    ))
    
    history = FileHistory(".codebase_rag_history")
    
    while True:
        try:
            question = prompt("\n❓ ", history=history).strip()
            
            if not question:
                continue
            
            if question.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye! 👋[/yellow]")
                break
            
            if question.lower() == "clear":
                console.clear()
                continue
            
            # Search and generate
            with console.status("[bold blue]Thinking..."):
                results = retriever.search(question, top_k=10)
                
                if not results:
                    console.print("[yellow]No results found.[/yellow]")
                    continue
                
                results = reranker.rerank(question, results, top_k=5)
                answer = generator.generate(question, results)
            
            console.print()
            console.print(Markdown(answer))
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
        except EOFError:
            break


@app.command()
def stats():
    """Show system statistics."""
    retriever, _, _ = get_components()
    
    stats = retriever.vector_store.get_stats()
    
    console.print(Panel.fit(
        f"[bold]Collection:[/bold] {stats['name']}\n"
        f"[bold]Total Chunks:[/bold] {stats['count']}",
        title="📊 System Statistics",
    ))


@app.command()
def reset():
    """Reset the system (delete all indexed data)."""
    if typer.confirm("⚠️ This will delete all indexed data. Continue?"):
        retriever, _, _ = get_components()
        retriever.vector_store.delete_collection()
        console.print("[green]✅ Collection deleted successfully.[/green]")


if __name__ == "__main__":
    app()
