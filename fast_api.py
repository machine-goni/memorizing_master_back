'''
fastapi 는 pip install 로 설치해줘야 하고
서버를 돌리기 위해 pip install "uvicorn[standard]" 도 실행
'''

# backend 를 FastAPI 로 구현

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware      # 보안을 위해 CORS 설정을 해줘야 한다.
from fastapi import Request                             # 들어오는 request 의 origin 을 확인해보고 싶으면 Request 를 import 해주면 된다.
from pydantic import BaseModel
from receive_requests import RecvRequests
#import logging

import atexit   # 프로그램 종료시 호출을 위해


# 설정 로깅
#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)


class User_inputs_summarize(BaseModel):
    original_text : str


# FastAPI instance
app = FastAPI()


#-- CORS 설정 ----------------

# 허용할 도메인 리스트
origins = [
    "*",
    #"https://legal-with-ai.pages.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def check_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    #print(f"origin: {origin}")

    # 요청 헤더의 Origin이 허용된 origins 목록에 없으면 403 오류 발생
    if (origin not in origins) and ("*" not in origins):
        raise HTTPException(status_code=403)

    response = await call_next(request)
    return response

#-------------------------------------------------------------------- CORS 설정 --


receiver = RecvRequests()


# 프로그램 종료 시 호출
def on_exit():
    print("프로그램 종료 중...")


atexit.register(on_exit)    # on_exit 등록


@app.post("/init")
async def operate():
    try:
        if receiver != None:
            #logging.info("Receiver is initialized")
            return True
        else:
            #logging.info("Receiver is not initialized")
            return False
    
    except Exception as e:
        #logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize")
async def operate(input:User_inputs_summarize):
    try:
        result = await receiver.summarize(input.original_text)
        #print(f"summarize: \n{result}")
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# For running the FastAPI server we need to run the following command:
# uvicorn fast_api:app --reload
# fast_api 는 실행할 FastAPI 가 구현되어있는 python script
# 커맨드를 실행하면 접속할 수 있는 local url 이 나온다
# http://127.0.0.1:8000/docs 를 열면 Swagger UI 를 볼 수 있다.