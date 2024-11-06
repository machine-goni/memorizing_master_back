from typing import TypedDict


# GraphState 상태를 저장하는 용도로 사용
class GraphState(TypedDict):
    context: str                    # 문서의 검색 결과
    answer: str                     # 답변
