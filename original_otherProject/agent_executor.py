from chatbot.agent import get_agent
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, BaseMessage
from chatbot.agent_tools import tool_from_name
from chatbot.llm_answer_parser import llm_answer_parser

from langchain_core.exceptions import OutputParserException 

from retrieve.query_enricher import QueryEnricher


def objecte2string(obj) -> str:
    """
    Recursively converts a nested structure of dicts, lists, and tuples into a single string.
    - dicts become "{key1: val1, key2: val2, …}"
    - lists become "[item1, item2, …]"
    - tuples become "(item1, item2, …)"
    - everything else is just str(obj)
    """
    if isinstance(obj, dict):
        items = []
        for key, val in obj.items():
            items.append(f"{key}: {objecte2string(val)}")
        return "{" + ", ".join(items) + "}"
    elif isinstance(obj, list):
        return "[" + ", ".join(objecte2string(item) for item in obj) + "]"
    elif isinstance(obj, tuple):
        return "(" + ", ".join(objecte2string(item) for item in obj) + ")"
    else:
        return str(obj)



class AgentExecutor:
    def __init__(self):
        self.agent = get_agent()

    def invoke(self, query, conversation):
        scratchpad = []
        q = QueryEnricher()
        info = q.get_info_to_enrich_query(query) # TODO
        
        try:
            ai_msg =  self.agent.invoke({"input": query, "chat_history": conversation, "info" : info})
            scratchpad.append(ai_msg)
        except:
            scratchpad.append(AIMessage("Could not understand the question"))
            ai_msg = AIMessage("Could not understand the question")
    
        print("tools   " + "-"*100)
        print(ai_msg.tool_calls)
        print("content " +"-"*100)
        print(ai_msg.content)
        print("message " +"-"*100)
        print(ai_msg)
        print("-"*100)

        final_tool_args = {}
        end = False
        while ai_msg.tool_calls:

            errors = ""
            for tool_call in ai_msg.tool_calls: 
                try:
                    if tool_call["name"].lower() == "final_answer":
                        final_tool_args = tool_call["args"]
                        end = True
                        break

                    tool = tool_from_name[tool_call["name"].lower()]
                    tool_output = tool.invoke(tool_call["args"])

                    print("tool ouput ->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                    print(tool_call["name"].lower(), tool_call["args"])

                    print(tool_output)

                    print(type(tool_output))
                    print("tool ouput <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                    #t = ToolMessage(
                    #    content=tool_output["stdout"],
                    #    artifact=tool_output,
                    #    tool_call_id=tool_call["id"]
                    #)
                    #scratchpad.append(t)
                    scratchpad.append(ToolMessage(objecte2string(tool_output), tool_call_id=tool_call["id"]))
                    #scratchpad.append(AIMessage(str(tool_output) + str(tool_call["id"])))
                except Exception as e:
                    print("An exception ocurred when calling a tool")
                    errors += "Your last tool call produced this error: " + str(e)

            if end:
                break

            try:
                ai_msg =  self.agent.invoke({"input": query, "chat_history": conversation, "scratchpad": scratchpad, "error_msg": errors, "info" : info})
                scratchpad.append(AIMessage(ai_msg.tool_calls))
            except:
                print("Error calling ")
                print({"input": query, "chat_history": conversation, "scratchpad": scratchpad, "error_msg": errors})
                print()
                scratchpad.append(AIMessage("Could not understand the question"))
                break

        response = {}
        if not end or ("answer" not in final_tool_args.keys() or 'sources' not in final_tool_args.keys() or 'language' not in final_tool_args.keys()):
            print("*"*20)
            print("CALLING LLM ANSWER PARSER")
            #si no ha cridat a final_answer, o esta mal formatejada
            try:
                answer = llm_answer_parser.invoke({"input": query, "chat_history": conversation, "scratchpad": scratchpad})
            except OutputParserException as e:
                    print("OutputParserException")
                    print("error: ")
                    print(str(e))
                    error_msg = "You last JSON output call gave this error, probably because you used double quotes quotes instead of single quotes" + str(e)
                    try:
                        def prune_empty(messages: list[BaseMessage]) -> list[BaseMessage]:
                            pruned = []
                            for m in messages:
                                # keep it if it has non-whitespace text...
                                content = getattr(m, "content", None)
                                if isinstance(content, str) and content.strip():
                                    pruned.append(m)
                                # ...or if it has a pending tool_call to run
                                elif getattr(m, "tool_calls", None):
                                    pruned.append(m)
                                # otherwise drop it
                            return pruned

                        clean_history   = prune_empty(conversation)
                        clean_scratch  = prune_empty(scratchpad)

                        ai_msg = llm_answer_parser.invoke({
                            "input": query,
                            "chat_history": clean_history,
                            "scratchpad": clean_scratch,
                            "error_msg": errors,
                        })


                        #
                        # answer = llm_answer_parser.invoke({"input": query, "chat_history": conversation, "scratchpad": scratchpad, "error_msg":error_msg })             
                    except:
                        answer = {"Sorry, something went wrong while processing your request. I couldn't understand your question. Please try rephrasing or ask again."}
            print(f"{answer=}")

            response = {
                "answer": answer.get("answer", answer.get("answ", "") ),
                "sources": answer.get("src", answer.get("sources", "") ),
                "language": answer.get("language", answer.get("lan", "") ),
            }
        else:
            response = {
                "answer": final_tool_args.get("answer", final_tool_args.get("answ", "") ),
                "sources": final_tool_args.get("src", final_tool_args.get("sources", "") ),
                "language": final_tool_args.get("language", final_tool_args.get("lan", "") ),
            }
        
        print( )

        return response
    
    def invoke_old(self, query, conversation):
        ai_msg =  self.agent.invoke({"input": query, "chat_history": conversation})

        scratchpad = [ai_msg]

        final = False
        while True: #ai_msg.tool_calls:
            print("OUTPUT" + "-"*100, flush=True)
            print(ai_msg)
            print("-"*100, flush=True)

            if ai_msg.content:
                scratchpad.append(AIMessage(ai_msg.content))
                print("CONTENT")
                print(ai_msg.content)
            
            for tool_call in ai_msg.tool_calls:
                                
                print("tool" + "*"*100, flush=True)
                print(tool_call, flush=True)
                print("*", flush=True)
                print(tool_call["name"].lower(), flush=True)
                print("end tool" + "*"*100, flush=True)
                
                tool = tool_from_name[tool_call["name"].lower()]

                tool_output = tool.invoke(tool_call["args"])
                scratchpad.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))

                if tool_call["name"].lower() == "final_answer" or "final_answer" in ai_msg.content:
                    print("FINAL ANSWER")
                    final = True
                    break

            if  "final_answer" in ai_msg.content:
                print("FINAL ANSWER CONTENT")
                final = True     

            if final:
                break

            ai_msg =  self.agent.invoke({"input": query, "chat_history": conversation, "scratchpad": scratchpad})


        print(scratchpad)


        return scratchpad[0].content