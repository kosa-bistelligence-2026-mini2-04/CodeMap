# Structured Repo Context (SRC) MCP Server

## Overview
`kvnpetit/structured-repo-context-mcp`는 AI 어시스턴트가 코드베이스를 보다 깊이 있게 이해하고 효율적으로 작업할 수 있도록 설계된 MCP(Model Context Protocol) 서버입니다. AI 모델에 저장소의 구조화된 컨텍스트를 제공하여 보다 정확한 코드 관련 작업을 수행할 수 있도록 지원합니다.

## Core Highlights
*   **시맨틱 코드 검색 (Semantic Code Search)**: 단순한 키워드 매칭을 넘어, 코드의 의미를 기반으로 한 검색 기능을 제공합니다.
*   **구조화된 컨텍스트 제공 (Structured Context)**: AI 모델이 단순히 파일의 텍스트를 읽는 것을 넘어, 전체 저장소의 구조적 문맥을 파악할 수 있도록 돕습니다.
*   **효율적인 코드 파싱 (Efficient Code Parsing)**: 추상 구문 트리(AST)를 분석하여 코드의 계층적 구조와 관계를 이해합니다.

## Tech Stack
*   **Language**: TypeScript
*   **Protocol**: Model Context Protocol (MCP)
*   **Parsing**: Tree-sitter (효율적인 코드 파싱 및 쿼리)
*   **Search**: Embeddings & Vector Search (시맨틱 검색 기능 구현)

## Architecture
MCP 호환 클라이언트(예: LobeHub 데스크톱 앱, Claude Desktop 등)와 연동되어 동작합니다. `npm`을 통해 글로벌로 설치되며, `src-mcp serve` 명령어로 실행됩니다. 클라이언트가 코드베이스에 대한 질문이나 검색을 요청하면, 서버는 내부적으로 Tree-sitter와 임베딩을 활용해 코드를 구문 분석하고 벡터 검색을 수행합니다. 이를 통해 얻은 구조화된 코드 정보(AST 등)를 다시 AI 모델에 전달하여, 표준 파일 읽기 방식보다 훨씬 정확하고 풍부한 코드 컨텍스트를 AI가 활용할 수 있게 하는 아키텍처를 가집니다.
