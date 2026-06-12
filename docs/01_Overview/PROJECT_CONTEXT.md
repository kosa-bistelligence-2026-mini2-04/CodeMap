# mini2 Project Context

- **Project Name**: CodeMap
- **Description**: GitHub Repository Analysis Chatbot Project.
- **Note**: This directory (`mini2`) is the root workspace for the CodeMap project.

## Architecture Standard
- FastAPI는 공식적인 표준 구조가 강제되지 않으므로, 본 프로젝트는 **Java Spring Boot 기반의 전형적인 REST API 아키텍처 철학**을 차용하여 설계되었습니다.
- **도메인 주도(DDD) 및 계층 분리**: `controller`, `service`, `repository`, `dto` 등의 명명 규칙을 준수하며 도메인(기능)별로 응집도를 높여 구성합니다.
- **로직과 자원의 엄격한 분리**: 비즈니스 로직(파이썬 코드)이 담긴 `app/` 폴더와 정적 자원(`static/`, `templates/`) 폴더를 자바의 `src/main/resources/` 철학처럼 최상위에서 엄격하게 분리하여 관리합니다.
