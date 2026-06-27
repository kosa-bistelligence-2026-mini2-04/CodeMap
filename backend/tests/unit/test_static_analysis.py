import os
import ast
import pytest

def test_static_analysis_for_pydantic_and_typing():
    """
    프로젝트 내의 Pydantic V1 잔재 및 Mutable Default 사용을 검증하는 정적 분석 테스트.
    Any/dict 남용은 당장 CI가 깨지지 않도록 경고(리포트) 용도로만 콘솔에 출력합니다.
    """
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app'))

    fatal_issues = []
    warning_issues = []

    for root, _, files in os.walk(app_dir):
        for file in files:
            if not file.endswith('.py'):
                continue
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, app_dir)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                fatal_issues.append(f"[Error Reading] {rel_path}: {str(e)}")
                continue

            # Pydantic V1 메소드 검출 (치명적 이슈)
            if '.dict(' in content:
                fatal_issues.append(f'[V1 Method] {rel_path} contains .dict() instead of .model_dump()')
            if '.parse_obj(' in content:
                fatal_issues.append(f'[V1 Method] {rel_path} contains .parse_obj() instead of .model_validate()')
            if 'class Config:' in content:
                fatal_issues.append(f'[V1 Config] {rel_path} uses class Config: instead of model_config = ConfigDict(...)')

            # AST 분석
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    # Any 사용 찾기 (경고)
                    if isinstance(node, ast.Name) and node.id == 'Any':
                        warning_issues.append(f'[Type Strictness] {rel_path}:{node.lineno} uses Any type hint')

                    # 함수 인자 중 Optional 없이 None을 기본값으로 가지는지 (단, | None 문법 제외) (치명적)
                    if isinstance(node, ast.FunctionDef):
                        num_defaults = len(node.args.defaults)
                        if num_defaults > 0:
                            args_with_defaults = node.args.args[-num_defaults:]
                            for arg, default in zip(args_with_defaults, node.args.defaults):
                                if isinstance(default, ast.Constant) and default.value is None:
                                    ann = arg.annotation
                                    is_optional = False
                                    if ann:
                                        ann_str = ast.unparse(ann)
                                        if 'Optional' in ann_str or '| None' in ann_str or 'None' in ann_str or 'Any' in ann_str:
                                            is_optional = True
                                    if ann and not is_optional:
                                        fatal_issues.append(f'[Nullable Safety] {rel_path}:{node.lineno} function {node.name} arg {arg.arg} defaults to None but is typed as {ast.unparse(ann)}')

                    # 데이터 불변성: mutable default arguments 확인 (치명적)
                    if isinstance(node, ast.FunctionDef):
                        for default in node.args.defaults:
                            if isinstance(default, (ast.List, ast.Dict)):
                                fatal_issues.append(f'[Mutable Default] {rel_path}:{node.lineno} function {node.name} uses mutable default argument')

                    # 모델 속성 중 Any 또는 dict 확인 (경고)
                    if isinstance(node, ast.AnnAssign):
                        if node.annotation:
                            try:
                                ann_str = ast.unparse(node.annotation)
                                if ann_str == 'dict':
                                    warning_issues.append(f'[Type Strictness] {rel_path}:{node.lineno} uses raw dict instead of Dict[K,V] or typed model')
                            except Exception:
                                pass
            except SyntaxError:
                fatal_issues.append(f"[Syntax Error] Cannot parse {rel_path}")

    # 발견된 경고 사항은 pytest 실행 시 콘솔에 출력 (-s 옵션 사용 시 확인 가능)
    if warning_issues:
        print("\n--- [Static Analysis Warnings (Type Strictness)] ---")
        for w in warning_issues:
            print(w)

    # 치명적 이슈(V1 문법 등)가 있으면 assert fail 로 CI를 깨뜨림
    assert len(fatal_issues) == 0, f"Static analysis found fatal issues:\n" + "\n".join(fatal_issues)
