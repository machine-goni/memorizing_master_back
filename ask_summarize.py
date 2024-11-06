# pip freeze > requirements.txt
# 위 명령어로 requirements.txt 를 뽑을 수 있다
# requirements.txt 를 사용해 일괄 설치하려면 아래명령어.
# pip install -r requirements.txt
# 만약 패키지간 호환성 문제로 에러가 날때 제안되는 방법은 2가지 이다.
'''
To fix this you could try to:
1. 지정한 패키지 버전의 범위를 느슨하게 합니다.
2. pip가 종속성 충돌을 해결하려고 시도할 수 있도록 패키지 버전을 제거하세요.
'''
# requirements.txt 를 사용해 일괄 삭제하려면 아래명령어.
# pip uninstall -r requirements.txt -y


import os
from dotenv import load_dotenv
import gc
#from memory_profiler import profile
import asyncio  # 동시실행 제어를 통한 데이터 무결성을 유지하기 위해 lock 사용

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.prompts import ChatPromptTemplate

# langgraph 구조에 필요한 패키지들
from GraphState import GraphState
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.checkpoint.memory import MemorySaver
from utils import format_docs, pretty_print, get_prompts
from operator import itemgetter
import pprint
from langgraph.errors import GraphRecursionError
from langchain_core.runnables import RunnableConfig


MAX_ORIGINAL_TEXT_LENGTH = 3000


class AskSummarize:
    
    def __init__(self):
        load_dotenv()
        os.environ['OPENAI_API_KEY'] = os.getenv("openai_api_key")
        
        # LLM Model
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
            
        # app.stream 에 넣을 config
        # recursion_limit: 최대 노드 실행 개수 지정 (13인 경우: 총 13개의 노드까지 실행). 구현된 노드의 갯수가 아니라 루프를 포함한 전체 실행 노드 개수. 
        # 만약에 5개의 노드가 돌고 돌아 3번씩 실행하게 되면 최소 15개는 되야 한다는 뜻이다.
        # thread_id: 그래프 실행 아이디 기록하고, 추후 추적 목적으로 활용
        self.config = RunnableConfig(recursion_limit=12, configurable={"thread_id": "memorizing_master"})
        
        # 동시사용 제어
        self.lock_llm = asyncio.Lock()
        
        
    # -- node 가 될 함수들 (langgraph 에서 node 는 GraphState 를 받고 GraphState 를 넘겨줘야 한다) --
    
    # LLM을 사용하여 답변을 생성
    #@profile
    async def llm_answer(self, state: GraphState) -> GraphState:
        async with self.lock_llm:
            original_text = state["context"]
            
            with get_openai_callback() as cb:
                prompt = ChatPromptTemplate.from_template(get_prompts("summarize"))
                
                qa_chain = (
                    {"context": itemgetter("context")}
                    | prompt | self.llm | StrOutputParser()
                )
                response = qa_chain.invoke({"context": original_text})
                
                #print('*** result ***')
                #print('result:', response)
                #print('---' * 20)
                print(cb)
            
            return GraphState(answer=response)
        
    # -- node 가 될 함수들 (langgraph 에서 node 는 GraphState 를 받고 GraphState 를 넘겨줘야 한다) --
    
    
    #@profile
    async def run_workflow(self, inputs: GraphState, app: CompiledGraph):
        answer = ""

        gc.collect()
        
        # app.stream을 통해 입력된 메시지에 대한 출력을 스트리밍
        # config 설정 안해주면 에러난다
        try:
            async for output in app.astream(inputs, config=self.config):        # 비동기
                # 출력된 결과에서 키와 값을 순회
                for key, value in output.items():
                    # 노드의 이름과 해당 노드에서 나온 출력을 출력
                    pprint.pprint(f"Output from node '{key}':")
                    #pprint.pprint("---")
                    # 출력 값 출력
                    #pprint.pprint(value, indent=2, width=80, depth=None)
                    
                if key == "llm_answer" and "answer" in value:
                    answer = value["answer"]
                
                # 각 출력 사이에 구분선을 추가
                #pprint.pprint("\n---\n")
                
        except GraphRecursionError as e:
            #pprint.pprint(f"Recursion limit reached: {e}")
            answer = f"excepttion: {e}"
            
        return answer
    
    
    # 구현된 node 와 edge 로 workflow 정의
    #@profile
    def build_workflow_summarize(self):
        # langgraph.graph에서 StateGraph와 END를 가져옵니다.
        workflow = StateGraph(GraphState)
        
        # original workflow
        workflow.add_node("llm_answer", self.llm_answer)
        workflow.add_edge("llm_answer", END)
        workflow.set_entry_point("llm_answer")

        app = workflow.compile(checkpointer=MemorySaver())
        
        return app
        
        
    #@profile
    async def summarize(self, original_text) -> dict:
        # token 수 관리차원에서 text 의 길이를 체크
        if len(original_text) <= MAX_ORIGINAL_TEXT_LENGTH:        
            inputs = GraphState(context=original_text)
            app = self.build_workflow_summarize()
            result = await self.run_workflow(inputs, app)
            
            result_dict = {"summarized_text":result}
        else:
            result_dict = {"error_msg":"글자수가 최대치를 초과 했습니다."}
            
        #print(f'result_dict: {result_dict}')
        
        return result_dict

