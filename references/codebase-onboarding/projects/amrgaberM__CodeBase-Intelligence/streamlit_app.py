import streamlit as st
import time
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="CodeLens - AI Code Intelligence",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .stApp { background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%); }
    .main-title { font-size: 3.5rem; font-weight: 700; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-align: center; margin-bottom: 0.5rem; letter-spacing: -0.02em; }
    .sub-title { font-size: 1.25rem; color: #94a3b8; text-align: center; margin-bottom: 3rem; font-weight: 400; }
    .feature-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin: 2rem 0; }
    .feature-box { background: rgba(30, 30, 50, 0.8); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 16px; padding: 2rem 1.5rem; text-align: center; transition: all 0.3s ease; }
    .feature-box:hover { border-color: rgba(99, 102, 241, 0.5); transform: translateY(-4px); box-shadow: 0 20px 40px rgba(99, 102, 241, 0.15); }
    .feature-icon { width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem; color: white; }
    .feature-title { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.5rem; }
    .feature-desc { font-size: 0.875rem; color: #64748b; line-height: 1.5; }
    .step-container { display: flex; justify-content: center; gap: 2rem; margin: 3rem 0; }
    .step-box { background: rgba(30, 30, 50, 0.6); border: 1px solid rgba(99, 102, 241, 0.15); border-radius: 16px; padding: 2rem; text-align: center; flex: 1; max-width: 300px; }
    .step-number { width: 40px; height: 40px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-weight: 700; color: white; font-size: 1.1rem; }
    .step-title { font-size: 1.1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.5rem; }
    .step-desc { font-size: 0.875rem; color: #64748b; }
    .repo-card { background: rgba(30, 30, 50, 0.6); border: 1px solid rgba(99, 102, 241, 0.15); border-radius: 12px; padding: 1.25rem; text-align: center; transition: all 0.2s ease; }
    .repo-card:hover { border-color: rgba(99, 102, 241, 0.4); }
    .repo-url { font-family: monospace; font-size: 0.8rem; color: #a5b4fc; background: rgba(99, 102, 241, 0.1); padding: 0.5rem 1rem; border-radius: 6px; margin-bottom: 0.5rem; word-break: break-all; }
    .repo-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .section-title { font-size: 1.5rem; font-weight: 600; color: #e2e8f0; text-align: center; margin: 3rem 0 2rem; }
    .chat-header { font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.25rem; }
    .chat-subheader { font-size: 1rem; color: #64748b; margin-bottom: 2rem; }
    .source-item { background: rgba(99, 102, 241, 0.1); border-left: 3px solid #6366f1; border-radius: 0 8px 8px 0; padding: 0.75rem 1rem; margin: 0.5rem 0; font-family: monospace; font-size: 0.8rem; color: #cbd5e1; }
    .stats-container { display: flex; gap: 1rem; margin: 1rem 0; }
    .stat-box { background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 1rem; text-align: center; flex: 1; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #a5b4fc; }
    .stat-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; }
    .result-title { font-size: 1.1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 1rem; }
    .estimate-box { background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 1rem; margin: 1rem 0; text-align: center; }
    .estimate-time { font-size: 1.25rem; font-weight: 600; color: #a5b4fc; }
    .estimate-label { font-size: 0.75rem; color: #94a3b8; }
    section[data-testid="stSidebar"] { background: rgba(15, 15, 35, 0.95); border-right: 1px solid rgba(99, 102, 241, 0.1); }
    section[data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }
    .stTextInput input { background: rgba(30, 30, 50, 0.8); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; color: #e2e8f0; padding: 0.75rem 1rem; }
    .stTextInput input:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2); }
    .stTextArea textarea { background: rgba(30, 30, 50, 0.8); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; color: #e2e8f0; }
    .stSelectbox > div > div { background: rgba(30, 30, 50, 0.8); border: 1px solid rgba(99, 102, 241, 0.3); color: #e2e8f0; }
    .stButton > button { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; border: none; border-radius: 8px; padding: 0.5rem 1.5rem; font-weight: 600; transition: all 0.2s ease; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4); }
    .stButton > button[kind="secondary"] { background: transparent; border: 1px solid rgba(99, 102, 241, 0.5); color: #a5b4fc; }
    .stChatMessage { background: rgba(30, 30, 50, 0.6); border: 1px solid rgba(99, 102, 241, 0.1); border-radius: 12px; padding: 1rem; }
    .stChatInputContainer { background: rgba(30, 30, 50, 0.8); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] { background: rgba(30, 30, 50, 0.6); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; color: #94a3b8; padding: 0.5rem 1rem; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-color: transparent; color: white; }
    .stSlider { color: #a5b4fc; }
    .streamlit-expanderHeader { background: rgba(99, 102, 241, 0.1); border-radius: 8px; color: #e2e8f0; }
    [data-testid="stMetricValue"] { color: #a5b4fc; }
    [data-testid="stMetricLabel"] { color: #64748b; }
    .stProgress > div > div { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); }
    hr { border-color: rgba(99, 102, 241, 0.1); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "retriever" not in st.session_state:
    st.session_state.retriever = None
    st.session_state.generator = None
    st.session_state.reranker = None
    st.session_state.intelligence = None
    st.session_state.indexed = False
    st.session_state.messages = []
    st.session_state.repo_name = ""
    st.session_state.files_count = 0
    st.session_state.chunks_count = 0
    st.session_state.files = None
    st.session_state.show_estimate = False
    st.session_state.estimated_time = 0

def clear_database():
    vectors_path = Path("data/vectors")
    repos_path = Path("data/repos")
    if vectors_path.exists():
        shutil.rmtree(vectors_path, ignore_errors=True)
    if repos_path.exists():
        shutil.rmtree(repos_path, ignore_errors=True)
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def estimate_time(repo_url: str) -> dict:
    """Estimate indexing time based on repo size."""
    import requests
    
    try:
        # Parse owner/repo from URL
        parts = repo_url.rstrip('/').rstrip('.git').split('/')
        owner, repo = parts[-2], parts[-1]
        
        # Get repo info from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            size_kb = data.get('size', 0)  # Size in KB
            
            # Estimate files (rough: 1 file per 5KB average)
            est_files = max(10, size_kb // 5)
            
            # Estimate chunks (roughly 3-5 chunks per file)
            est_chunks = est_files * 4
            
            # Time estimate: ~0.3 seconds per chunk for embedding
            est_seconds = int(est_chunks * 0.3) + 10  # +10 for cloning
            
            return {
                "success": True,
                "repo_name": data.get('full_name', f"{owner}/{repo}"),
                "size_kb": size_kb,
                "stars": data.get('stargazers_count', 0),
                "est_files": est_files,
                "est_chunks": est_chunks,
                "est_seconds": est_seconds,
                "est_time_str": f"{est_seconds // 60}m {est_seconds % 60}s" if est_seconds >= 60 else f"{est_seconds}s"
            }
    except Exception as e:
        pass
    
    return {"success": False}

def index_repository(repo_url, progress_callback=None):
    from src.ingestion import GitHubLoader
    from src.chunking import ASTChunker
    from src.retrieval import HybridRetriever, LightweightReranker
    from src.generation import CodeGenerator, CodeIntelligence
    
    if progress_callback:
        progress_callback(10, "Cloning repository...")
    
    loader = GitHubLoader()
    files = loader.clone_repo(repo_url)
    
    if progress_callback:
        progress_callback(30, f"Parsing {len(files)} files...")
    
    chunker = ASTChunker()
    chunks = chunker.chunk_files(files)
    
    if progress_callback:
        progress_callback(50, f"Indexing {len(chunks)} chunks...")
    
    retriever = HybridRetriever()
    generator = CodeGenerator()
    reranker = LightweightReranker()
    retriever.index(chunks, files)
    
    if progress_callback:
        progress_callback(90, "Building intelligence...")
    
    intelligence = CodeIntelligence(retriever, generator)
    
    return {
        "files": files,
        "chunks": chunks,
        "retriever": retriever,
        "generator": generator,
        "reranker": reranker,
        "intelligence": intelligence,
        "repo_name": loader._parse_repo_name(repo_url)
    }

# Sidebar
with st.sidebar:
    st.markdown("### CodeLens")
    st.markdown('<p style="color: #64748b; font-size: 0.875rem;">AI-Powered Code Intelligence</p>', unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown('<p style="color: #e2e8f0; font-weight: 500; margin-bottom: 0.5rem;">Repository URL</p>', unsafe_allow_html=True)
    repo_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repo",
        label_visibility="collapsed"
    )
    
    # Estimate button
    if repo_url and not st.session_state.get("indexed", False):
        if st.button("Estimate Time", key="estimate_btn", use_container_width=True):
            with st.spinner("Checking repository..."):
                estimate = estimate_time(repo_url)
                if estimate["success"]:
                    st.session_state.show_estimate = True
                    st.session_state.estimate_data = estimate
                else:
                    st.warning("Could not fetch repo info. Try indexing directly.")
        
        # Show estimate if available
        if st.session_state.get("show_estimate", False) and "estimate_data" in st.session_state:
            est = st.session_state.estimate_data
            st.markdown(f"""
            <div class="estimate-box">
                <div class="estimate-label">Estimated Time</div>
                <div class="estimate-time">{est['est_time_str']}</div>
                <div class="estimate-label" style="margin-top: 0.5rem;">
                    ~{est['est_files']} files | ~{est['est_chunks']} chunks | {est['size_kb']} KB
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        index_btn = st.button("Index", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.button("Clear", type="secondary", use_container_width=True)
    
    if clear_btn:
        clear_database()
        st.rerun()
    
    if index_btn and repo_url:
        try:
            clear_database()
            
            progress_bar = st.progress(0, text="Starting...")
            status_text = st.empty()
            
            def update_progress(pct, text):
                progress_bar.progress(pct, text=text)
                status_text.markdown(f'<p style="color: #94a3b8; font-size: 0.8rem;">{text}</p>', unsafe_allow_html=True)
            
            start_time = time.time()
            result = index_repository(repo_url, update_progress)
            elapsed = time.time() - start_time
            
            progress_bar.progress(100, text="Complete!")
            status_text.markdown(f'<p style="color: #10b981; font-size: 0.8rem;">Completed in {elapsed:.1f}s</p>', unsafe_allow_html=True)
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            st.session_state.files = result["files"]
            st.session_state.retriever = result["retriever"]
            st.session_state.generator = result["generator"]
            st.session_state.reranker = result["reranker"]
            st.session_state.intelligence = result["intelligence"]
            st.session_state.repo_name = result["repo_name"]
            st.session_state.files_count = len(result["files"])
            st.session_state.chunks_count = len(result["chunks"])
            st.session_state.indexed = True
            st.session_state.messages = []
            st.session_state.show_estimate = False
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    if st.session_state.get("indexed", False):
        st.divider()
        st.markdown('<p style="color: #e2e8f0; font-weight: 500;">Statistics</p>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="stats-container">
            <div class="stat-box">
                <div class="stat-value">{st.session_state.get("files_count", 0)}</div>
                <div class="stat-label">Files</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{st.session_state.get("chunks_count", 0)}</div>
                <div class="stat-label">Chunks</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f'<p style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">{st.session_state.get("repo_name", "")}</p>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown('<p style="color: #e2e8f0; font-weight: 500;">Settings</p>', unsafe_allow_html=True)
        top_k = st.slider("Number of results", 1, 10, 5)
        use_reranking = st.checkbox("Enable reranking", value=True)
    else:
        top_k = 5
        use_reranking = True

# Main content
if not st.session_state.get("indexed", False):
    st.markdown('<h1 class="main-title">CodeLens</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Understand any codebase in seconds with AI-powered intelligence</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-box">
            <div class="feature-icon">Q</div>
            <div class="feature-title">Natural Language Q and A</div>
            <div class="feature-desc">Ask questions about code in plain English and get precise answers</div>
        </div>
        <div class="feature-box">
            <div class="feature-icon">S</div>
            <div class="feature-title">Smart Code Search</div>
            <div class="feature-desc">Hybrid search combining semantic understanding and keyword matching</div>
        </div>
        <div class="feature-box">
            <div class="feature-icon">D</div>
            <div class="feature-title">Dependency Analysis</div>
            <div class="feature-desc">Understand how files and functions connect across the codebase</div>
        </div>
        <div class="feature-box">
            <div class="feature-icon">A</div>
            <div class="feature-title">AST-Based Chunking</div>
            <div class="feature-desc">Intelligent code parsing that understands structure, not just text</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h2 class="section-title">How It Works</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="step-container">
        <div class="step-box">
            <div class="step-number">1</div>
            <div class="step-title">Paste Repository URL</div>
            <div class="step-desc">Enter any public GitHub repository URL in the sidebar</div>
        </div>
        <div class="step-box">
            <div class="step-number">2</div>
            <div class="step-title">Click Index</div>
            <div class="step-desc">AI analyzes the entire codebase structure and semantics</div>
        </div>
        <div class="step-box">
            <div class="step-number">3</div>
            <div class="step-title">Ask Questions</div>
            <div class="step-desc">Chat naturally about code structure, logic, and implementation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h2 class="section-title">Try These Repositories</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="repo-card">
            <div class="repo-url">https://github.com/tiangolo/typer</div>
            <div class="repo-label">CLI Framework</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="repo-card">
            <div class="repo-url">https://github.com/psf/requests</div>
            <div class="repo-label">HTTP Library</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="repo-card">
            <div class="repo-url">https://github.com/pallets/flask</div>
            <div class="repo-label">Web Framework</div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.markdown('<h1 class="chat-header">CodeLens</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="chat-subheader">Analyzing: {st.session_state.get("repo_name", "")}</p>', unsafe_allow_html=True)
    
    # Feature tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Chat", "Explain Function", "Find Similar", "Documentation", "Analyze"])
    
    with tab1:
        st.markdown('<p style="color: #94a3b8; margin-bottom: 1rem;">Ask any question about the codebase</p>', unsafe_allow_html=True)
        
        for msg in st.session_state.get("messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("View Sources"):
                        for src in msg["sources"]:
                            st.markdown(f'<div class="source-item">{src}</div>', unsafe_allow_html=True)
        
        if prompt := st.chat_input("Ask about the codebase..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        start = time.time()
                        retriever = st.session_state.get("retriever")
                        generator = st.session_state.get("generator")
                        reranker = st.session_state.get("reranker")
                        
                        results = retriever.search(prompt, top_k=top_k*2)
                        
                        if results and use_reranking:
                            results = reranker.rerank(prompt, results, top_k=top_k)
                        elif results:
                            results = results[:top_k]
                        
                        if results:
                            answer = generator.generate(prompt, results)
                        else:
                            answer = "No relevant code found. Try a different question."
                        
                        elapsed = time.time() - start
                    except Exception as e:
                        answer = f"Error: {str(e)}"
                        results = []
                        elapsed = 0
                
                st.markdown(answer)
                
                sources = []
                if results:
                    with st.expander("View Sources"):
                        for i, r in enumerate(results[:5], 1):
                            meta = r.get("metadata", {})
                            src = f"{meta.get('file_path', 'Unknown')} : {meta.get('name', 'Unknown')} ({meta.get('chunk_type', 'code')})"
                            sources.append(src)
                            st.markdown(f'<div class="source-item">{i}. {src}</div>', unsafe_allow_html=True)
                
                st.caption(f"Response time: {elapsed:.2f}s")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
    
    with tab2:
        st.markdown('<p style="color: #94a3b8; margin-bottom: 1rem;">Get detailed explanation of any function or class</p>', unsafe_allow_html=True)
        
        func_name = st.text_input("Function or class name", placeholder="e.g., parse_arguments, UserModel")
        file_path = st.text_input("File path (optional)", placeholder="e.g., src/utils.py")
        
        if st.button("Explain", key="explain_btn"):
            if func_name:
                with st.spinner("Analyzing function..."):
                    try:
                        intelligence = st.session_state.get("intelligence")
                        result = intelligence.explain_function(func_name, file_path if file_path else None)
                        
                        if "error" in result:
                            st.warning(result["error"])
                        else:
                            st.markdown(f'<div class="result-title">Explanation: {result["function_name"]}</div>', unsafe_allow_html=True)
                            st.markdown(f'**File:** {result["file_path"]} (lines {result.get("start_line", "?")}-{result.get("end_line", "?")})')
                            st.markdown("---")
                            st.markdown(result["explanation"])
                            
                            with st.expander("View Source Code"):
                                st.code(result["code"], language="python")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a function name.")
    
    with tab3:
        st.markdown('<p style="color: #94a3b8; margin-bottom: 1rem;">Find similar code patterns in the codebase</p>', unsafe_allow_html=True)
        
        code_snippet = st.text_area("Paste code snippet", placeholder="def example():\n    pass", height=150)
        
        if st.button("Find Similar", key="similar_btn"):
            if code_snippet:
                with st.spinner("Searching..."):
                    try:
                        intelligence = st.session_state.get("intelligence")
                        results = intelligence.find_similar_code(code_snippet, top_k=5)
                        
                        if results:
                            st.markdown('<div class="result-title">Similar Code Found</div>', unsafe_allow_html=True)
                            
                            for i, r in enumerate(results, 1):
                                with st.expander(f"{i}. {r['file']} - {r['name']} (Score: {r['similarity_score']:.3f})"):
                                    st.markdown(f"**Type:** {r['type']} | **Line:** {r['line']}")
                                    st.code(r["code"], language="python")
                        else:
                            st.warning("No similar code found.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please paste a code snippet.")
    
    with tab4:
        st.markdown('<p style="color: #94a3b8; margin-bottom: 1rem;">Auto-generate documentation for files</p>', unsafe_allow_html=True)
        
        files = st.session_state.get("files", [])
        file_paths = [f.path for f in files] if files else []
        
        selected_file = st.selectbox("Select a file", file_paths if file_paths else ["No files available"])
        
        if st.button("Generate Docs", key="docs_btn"):
            if selected_file and selected_file != "No files available":
                with st.spinner("Generating documentation..."):
                    try:
                        intelligence = st.session_state.get("intelligence")
                        docs = intelligence.generate_documentation(selected_file)
                        
                        st.markdown(f'<div class="result-title">Documentation: {selected_file}</div>', unsafe_allow_html=True)
                        st.markdown(docs)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab5:
        st.markdown('<p style="color: #94a3b8; margin-bottom: 1rem;">Get high-level analysis of the codebase</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Analyze Codebase", key="analyze_btn", use_container_width=True):
                with st.spinner("Analyzing..."):
                    try:
                        intelligence = st.session_state.get("intelligence")
                        stats = intelligence.analyze_codebase()
                        st.session_state.codebase_stats = stats
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        with col2:
            if st.button("Find Usages", key="usage_btn", use_container_width=True):
                st.session_state.show_usage_input = True
        
        if "codebase_stats" in st.session_state:
            stats = st.session_state.codebase_stats
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Files", stats.get('total_files', 0))
            with c2:
                st.metric("Code Chunks", stats.get('total_chunks', 0))
            with c3:
                st.metric("Classes", len(stats.get('classes', [])))
            
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Classes**")
                for cls in stats.get("classes", [])[:10]:
                    st.markdown(f'<div class="source-item">{cls["name"]} - {cls["file"]}</div>', unsafe_allow_html=True)
            
            with c2:
                st.markdown("**Functions**")
                for func in stats.get("functions", [])[:10]:
                    st.markdown(f'<div class="source-item">{func["name"]} - {func["file"]}</div>', unsafe_allow_html=True)
        
        if st.session_state.get("show_usage_input", False):
            st.markdown("---")
            usage_name = st.text_input("Enter function/class name to find usages", key="usage_input")
            
            if st.button("Search Usages", key="search_usage_btn"):
                if usage_name:
                    with st.spinner("Finding usages..."):
                        try:
                            intelligence = st.session_state.get("intelligence")
                            usages = intelligence.find_usages(usage_name)
                            
                            st.markdown(f'<div class="result-title">Usages of: {usages["name"]}</div>', unsafe_allow_html=True)
                            st.markdown(f"**Total found:** {usages['total_usages']}")
                            
                            usage_data = usages.get("usages", {})
                            
                            if usage_data.get("definition"):
                                st.markdown("**Definition:**")
                                d = usage_data["definition"]
                                st.markdown(f'<div class="source-item">{d["file"]} (line {d["line"]})</div>', unsafe_allow_html=True)
                            
                            if usage_data.get("calls"):
                                st.markdown("**Calls:**")
                                for call in usage_data["calls"][:5]:
                                    st.markdown(f'<div class="source-item">{call["file"]} (line {call["line"]})</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
