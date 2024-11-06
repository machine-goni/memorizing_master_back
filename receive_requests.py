# backend main code 로 frontend 의 입력을 전달할 receiver

from ask_summarize import AskSummarize


class RecvRequests:
    def __init__(self):
        self.ask_instance = AskSummarize()
    

    async def summarize(self, original_text) -> dict:
        result = await self.ask_instance.summarize(original_text)
            
        result_data = {}
        result_data["summarized_text"] = result.get("summarized_text")
        result_data["error_msg"] = result.get("error_msg")
        
        #print(f"RecvRequests summarize: \n{result_data}")
        return result_data
    
    