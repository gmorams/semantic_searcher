from langchain_core.messages import HumanMessage, AIMessage
from utils import measure_time
from chatbot.agent_executor import AgentExecutor
from utils import SingletonMeta

class ChatBot(metaclass=SingletonMeta):

    def __init__(self):
        self.agent_executor = AgentExecutor()
    
    @measure_time
    def ask_question(self, question, conversation):



        print(conversation)
        conv = []
        for turn in conversation:
            if "user" in turn:
                conv.append(HumanMessage(content=turn["user"]))
            if "chatbot" in turn:
                conv.append(AIMessage(content=turn["chatbot"]))

        print(conv)
        answer, src, response = self.call_executor(question, conv)

        print(answer)
        return {"response": answer, "src": (src if src else ""), "fullAnswer": str(response)}

    def call_executor(self, question, conversation):

        
        response = self.agent_executor.invoke(question, conversation)
    

        return  response["answer"] , response["sources"], response