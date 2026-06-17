import asyncio
import time
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from app.models.schemas import (
    ProviderCatalog,
    ModelInfo,
    AnalyzeRequest,
    AnalyzeResponse,
    ReportJsonResponse,
    Recommendation,
    ConflictResolution,
    CommunityMetrics,
    GuardrailTelemetry,
    LineRisk
)
from app.api.progress_bus import progress_bus

router = APIRouter()

# In-memory database for mock reports
analyses_db: dict[str, dict] = {}
# In-memory history list
history_db: list[dict] = []

# Populate initial history and mock reports for demonstrations
MOCK_JOBS = {
    "numpy-analysis-job": {
        "path": "https://github.com/numpy/numpy",
        "source": "github",
        "model": "gpt-4o",
        "created_at": int(time.time() - 3600),
        "completed_at": int(time.time() - 3550),
        "status": "completed",
        "health_score": 88,
        "executive_summary": "NumPy relies heavily on highly-optimized C loops and SIMD vectorization. The core memory layout utilizes contiguous strided Ndarrays. Most matrix arithmetic routes directly to BLAS/LAPACK implementations. Low-level performance bottlenecks exist in the ufunc outer loop dispatching logic, which is currently undergoing refactoring to modern C++ templates.",
        "key_strengths": [
            "Highly efficient vectorization via SIMD configuration pipelines",
            "Zero-copy memory slicing and advanced layout striding",
            "Direct bindings to industry-standard C BLAS/LAPACK packages"
        ],
        "key_risks": [
            "Extremely high code complexity in legacy C macros (ufunc loops)",
            "Fragmented memory management between Python allocator and C allocations"
        ],
        "recommendations": [
            Recommendation(
                title="Migrate macro-based ufuncs to C++ templates",
                detail="Legacy C preprocessor macros in 'numpy/core/src/multiarray/ufunc_object.c' hinder readability and maintainability. Replacing them with C++ metaprogramming will improve compile-time safety.",
                affected_files=["numpy/core/src/multiarray/ufunc_object.c", "numpy/core/src/umath/ufunc_dispatch.cpp"],
                priority="high"
            ),
            Recommendation(
                title="Sanitize inter-thread GIL releases",
                detail="Ensure GIL releases are properly scoped and don't lead to race conditions during multi-threaded slicing in array expressions.",
                affected_files=["numpy/core/src/multiarray/array_assign.c"],
                priority="medium"
            )
        ],
        "conflicts": [
            ConflictResolution(
                module="ufunc_object.c",
                static_view="Dead code detected in legacy dispatching paths. Recommend aggressive deprecation.",
                behavior_view="Active critical runtime path under SIMD execution. Deprecation would break SIMD optimizations.",
                final_recommendation="Preserve code but wrap in modern C++ templates to unify execution pathways.",
                judge_model="gpt-4o",
                escalated=False,
                confidence=0.92
            )
        ],
        "community": CommunityMetrics(
            commits_per_week=45.2,
            avg_issue_response_hours=3.5,
            unique_contributors=142,
            top_contributors=["charlesrharris", "seberg", "rgommers"],
            is_degraded=False
        ),
        "file_heatmap": {
            "numpy/core/src/multiarray/ufunc_object.c": [
                LineRisk(line=145, risk_level="critical", reason="Unbounded buffer write in macro dispatching loop", metric="complexity"),
                LineRisk(line=312, risk_level="high", reason="GIL released without proper thread context cleanup", metric="maintainability")
            ],
            "numpy/core/src/multiarray/array_assign.c": [
                LineRisk(line=78, risk_level="medium", reason="Redundant copying of strided layout configurations", metric="coverage")
            ]
        },
        "guardrail": GuardrailTelemetry(
            regex_blocked=[],
            semantic_filtered=[],
            regenerate_count=0,
            fallback_triggered=False,
            input_secrets_redacted=0,
            self_check_warnings=[]
        ),
        "durations": {
            "static_analyzer": 12450,
            "behavior_inferer": 18200,
            "community_assessor": 5400,
            "reporter": 8100
        },
        "html_report": """
        <div class="space-y-4">
            <h2>Detailed NumPy Architecture Report</h2>
            <p>This report covers the deep structural analysis of the NumPy ndarray and ufunc dispatch pipeline.</p>
            <h3>1. Ndarray Memory Topology</h3>
            <p>The core ndarray class is backed by a continuous block of memory mapped through a strided coordinate system. Slicing operations are zero-copy, shifting only the offsets and strides.</p>
            <h3>2. Ufunc Dispatches</h3>
            <p>The universal function (ufunc) execution layer resolves loops dynamically depending on alignment and memory continuity:</p>
            <ul>
                <li>Contiguous 1D loops trigger aligned compiler vectorization.</li>
                <li>Strided multi-dimensional loops fall back to nested pointer increments.</li>
            </ul>
        </div>
        """
    },
    "fastapi-analysis-job": {
        "path": "https://github.com/tiangolo/fastapi",
        "source": "github",
        "model": "gpt-4o",
        "created_at": int(time.time() - 7200),
        "completed_at": int(time.time() - 7160),
        "status": "completed",
        "health_score": 95,
        "executive_summary": "FastAPI leverages Pydantic for request/response serialization and Starlette for ASGI routing. Execution flow is driven by asyncio event loops. Route mapping reveals clean dependency-injection flows. Code risks are exceptionally low, with main hotspots centered around custom dynamic parameter parsing and signature matching.",
        "key_strengths": [
            "Extremely high code readability with strict type hints",
            "Highly performant async ASGI routing through Starlette",
            "Automated OpenAPI schema generation at runtime"
        ],
        "key_risks": [
            "High runtime overhead in dynamic inspect-module signatures",
            "Deep dependency coupling with specific Pydantic versions"
        ],
        "recommendations": [
            Recommendation(
                title="Optimize parameter extraction caching",
                detail="Caching signature parsing in 'fastapi/dependencies/utils.py' will reduce request serialization latency under high load.",
                affected_files=["fastapi/dependencies/utils.py"],
                priority="medium"
            )
        ],
        "conflicts": [],
        "community": CommunityMetrics(
            commits_per_week=12.8,
            avg_issue_response_hours=24.5,
            unique_contributors=318,
            top_contributors=["tiangolo", "dmontagu", "Kludex"],
            is_degraded=False
        ),
        "file_heatmap": {
            "fastapi/dependencies/utils.py": [
                LineRisk(line=254, risk_level="medium", reason="Dynamic introspection runtime penalty on every route invocation", metric="complexity")
            ]
        },
        "guardrail": GuardrailTelemetry(
            regex_blocked=[],
            semantic_filtered=[],
            regenerate_count=0,
            fallback_triggered=False,
            input_secrets_redacted=1,
            self_check_warnings=[]
        ),
        "durations": {
            "static_analyzer": 8500,
            "behavior_inferer": 11200,
            "community_assessor": 3800,
            "reporter": 4500
        },
        "html_report": """
        <div class="space-y-4">
            <h2>FastAPI Architecture Review</h2>
            <p>Comprehensive review of async routes and validation layers.</p>
            <h3>Dependency Injection</h3>
            <p>FastAPI uses Pydantic models to inspect function signatures at start time, mapping dependencies recursively to solve DI graphs on requests.</p>
        </div>
        """
    }
}

# Seed database
for jid, data in MOCK_JOBS.items():
    history_db.append({
        "job_id": jid,
        "source": data["source"],
        "path": data["path"],
        "status": data["status"],
        "created_at": data["created_at"],
        "completed_at": data["completed_at"],
        "total_pipeline_ms": sum(data["durations"].values()),
        "error_message": None,
        "model_used": data["model"],
        "force_refresh": False
    })
    
    analyses_db[jid] = ReportJsonResponse(
        job_id=jid,
        status="completed",
        completed_at=datetime.fromtimestamp(data["completed_at"]).isoformat(),
        total_pipeline_ms=sum(data["durations"].values()),
        recommendations=data["recommendations"],
        conflicts_resolved=data["conflicts"],
        community=data["community"],
        html_report=data["html_report"],
        file_heatmap=data["file_heatmap"],
        guardrail_telemetry=data["guardrail"],
        agent_durations=data["durations"],
        executive_summary=data["executive_summary"],
        health_score=data["health_score"],
        key_strengths=data["key_strengths"],
        key_risks=data["key_risks"],
        summary_confidence=0.95
    ).dict()


@router.get("/models", response_model=ProviderCatalog)
async def get_models():
    """Return mock LLM catalog."""
    return ProviderCatalog(
        provider="openai",
        base_url=None,
        default_model="gpt-4o",
        models=[
            ModelInfo(id="gpt-4o", label="GPT-4o (Standard)", hint="Balanced speed and deep reasoning capability."),
            ModelInfo(id="gpt-4-turbo", label="GPT-4 Turbo", hint="Extended context window for massive codebases."),
            ModelInfo(id="gpt-3.5-turbo", label="GPT-3.5 Turbo", hint="Cost-efficient and super fast scan option."),
        ]
    )


async def simulate_analysis_pipeline(job_id: str, path: str, source: str, model: str):
    """Simulate async progress steps and broadcast through progress_bus."""
    agents = ["static_analyzer", "behavior_inferer", "community_assessor", "reporter"]
    durations = {
        "static_analyzer": 2.0,
        "behavior_inferer": 3.0,
        "community_assessor": 1.5,
        "reporter": 2.0
    }
    
    try:
        # 1. Queued state
        await asyncio.sleep(1.0)
        
        # 2. Iterate Agents
        for agent in agents:
            # Send status: running
            await progress_bus.publish(job_id, {
                "type": "agent_status",
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent,
                "status": "running",
                "progress": 10,
                "stage_label": f"Scanning dependencies for {agent}..."
            })
            
            # Simulate progress steps
            for p in [30, 60, 80]:
                await asyncio.sleep(durations[agent] / 4.0)
                await progress_bus.publish(job_id, {
                    "type": "agent_status",
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent": agent,
                    "status": "running",
                    "progress": p,
                    "stage_label": f"Analyzing code syntax in {agent}..."
                })
            
            # Send conflict warning on behavior_inferer for visual test
            if agent == "behavior_inferer":
                await progress_bus.publish(job_id, {
                    "type": "conflict_detected",
                    "job_id": job_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "modules": ["main.py", "auth.py"],
                    "count": 1
                })
                await asyncio.sleep(0.5)

            # Completed agent
            await progress_bus.publish(job_id, {
                "type": "agent_completed",
                "job_id": job_id,
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent,
                "duration_ms": int(durations[agent] * 1000),
                "summary": f"{agent.replace('_', ' ').capitalize()} finished successfully."
            })
            await asyncio.sleep(0.5)

        # 3. Pipeline completed, compile final mock report
        completed_timestamp = int(time.time())
        total_time_ms = int(sum(durations.values()) * 1000 + 3000)
        
        # Save to database
        mock_report = ReportJsonResponse(
            job_id=job_id,
            status="completed",
            completed_at=datetime.utcfromtimestamp(completed_timestamp).isoformat() + "Z",
            total_pipeline_ms=total_time_ms,
            recommendations=[
                Recommendation(
                    title="Implement async route handlers",
                    detail=f"Detected synchronous blockages in IO boundaries of {path}. Wrapping them in async def handlers prevents ASGI event thread locking.",
                    affected_files=["app/main.py", "app/api/auth.py"],
                    priority="high"
                ),
                Recommendation(
                    title="Add input validation guardrails",
                    detail="Ensure user input parameters are strictly validated using Pydantic schemas to avoid raw memory injection leaks.",
                    affected_files=["app/models/schemas.py"],
                    priority="medium"
                )
            ],
            conflicts_resolved=[
                ConflictResolution(
                    module="app/main.py",
                    static_view="Unused open parameters. Safe to restrict.",
                    behavior_view="Active parameters invoked by integration test scripts.",
                    final_recommendation="Restrict input parameters but add mock payloads to integration suites.",
                    judge_model=model,
                    escalated=False,
                    confidence=0.89
                )
            ],
            community=CommunityMetrics(
                commits_per_week=8.5,
                avg_issue_response_hours=12.0,
                unique_contributors=14,
                top_contributors=["dev-lead", "coder-star"],
                is_degraded=False
            ),
            html_report=f"""
            <div class="space-y-4">
                <h2>Analysis Guideline: {path}</h2>
                <p>Generated onboarding playbook. Framework detected: Python FastAPI structure.</p>
                <h3>API Routing Design</h3>
                <p>Router configurations are properly segmented under app/api/ paths. Recommended additions: CORS middleware guards.</p>
            </div>
            """,
            file_heatmap={
                "app/main.py": [
                    LineRisk(line=42, risk_level="critical", reason="Blocking sync execution within async routing loop", metric="complexity"),
                    LineRisk(line=88, risk_level="low", reason="Missing log decorators for auditing boundaries", metric="maintainability")
                ],
                "app/api/auth.py": [
                    LineRisk(line=12, risk_level="high", reason="Hardcoded auth algorithm type", metric="complexity")
                ]
            },
            guardrail_telemetry=GuardrailTelemetry(
                regex_blocked=[],
                semantic_filtered=[],
                regenerate_count=0,
                fallback_triggered=False,
                input_secrets_redacted=0,
                self_check_warnings=[]
            ),
            agent_durations={k: int(v * 1000) for k, v in durations.items()},
            executive_summary=f"Analysis of repository '{path}' completed successfully. The code utilizes standard web structures. Optimization zones are located within the network payload handlers. Community metrics show high responsiveness with active maintainers.",
            health_score=91,
            key_strengths=["Clean modular router design", "Ready-to-run pytest suite configuration"],
            key_risks=["Synchronous blockages in router threads", "Over-scoped route authorization parameters"],
            summary_confidence=0.90
        ).dict()
        
        analyses_db[job_id] = mock_report
        
        # Add to history
        history_db.append({
            "job_id": job_id,
            "source": source,
            "path": path,
            "status": "completed",
            "created_at": completed_timestamp - int(total_time_ms / 1000),
            "completed_at": completed_timestamp,
            "total_pipeline_ms": total_time_ms,
            "error_message": None,
            "model_used": model,
            "force_refresh": False
        })
        
        # Broadcast completed
        await progress_bus.publish(job_id, {
            "type": "completed",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "report_url": f"/api/report/{job_id}",
            "total_duration_ms": total_time_ms
        })
        
    except Exception as e:
        await progress_bus.publish(job_id, {
            "type": "failed",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_code": "PIPELINE_ERROR",
            "message": str(e)
        })


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Start mock async repository analysis."""
    job_id = str(uuid.uuid4())
    created_time = datetime.utcnow().isoformat() + "Z"
    
    # Register background simulator
    background_tasks.add_task(
        simulate_analysis_pipeline,
        job_id,
        payload.path,
        payload.source,
        payload.model or "gpt-4o"
    )
    
    return AnalyzeResponse(
        job_id=job_id,
        status="queued",
        created_at=created_time,
        ws_url=f"/ws/progress/{job_id}" # Resolved at frontend via buildWsUrl
    )


@router.get("/analyses")
async def get_analyses(limit: int = 30):
    """Return historical jobs (sorted by newest)."""
    sorted_history = sorted(history_db, key=lambda x: x["created_at"], reverse=True)
    return {"items": sorted_history[:limit]}


@router.get("/report/{job_id}")
async def get_report(job_id: str, format: str = Query("json", regex="^(json|html)$")):
    """Get report output as JSON structure or raw HTML text."""
    if job_id not in analyses_db:
        raise HTTPException(status_code=404, detail="Job ID not found")
        
    report = analyses_db[job_id]
    if format == "html":
        return report.get("html_report") or "<div>No HTML report content available</div>"
    
    return report
