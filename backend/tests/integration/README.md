# Integration tests

LangGraph 흐름, PARSE → EMBED 연결, PostgreSQL·pgvector 및 실제 서비스 경계를 확인한다. 외부 모델이 필요한 테스트는 환경 변수로 명시적으로 활성화하고 기본 단위 테스트와 분리한다.
