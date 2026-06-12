from fastapi import FastAPI

# TODO: 추후 공통(common) 설정(CORS, 예외처리 등)을 불러와서 적용합니다.
# from app.common.config import ...
# from app.common.exception import ...

app = FastAPI(
    title="CodeMap API",
    description="Domain-Driven FastAPI Application",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}

# TODO: 추후 도메인별(user, analysis 등) 라우터를 아래에 연결(include)합니다.
# app.include_router(user_controller.router, prefix="/api/v1/users")
# app.include_router(analysis_controller.router, prefix="/api/v1/analysis")
