# Standard library
import re
import json
import ast
from typing import Union, List

# Third-party
import json5
from pydantic import BaseModel, Field

# LangChain-core
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage
from langchain_core.exceptions import OutputParserException             # :contentReference[oaicite:1]{index=1}
from langchain_core.outputs.generation import Generation                # :contentReference[oaicite:2]{index=2}
import re

# Your application
from chatbot.llm import get_llm

#############################################################################################################

def parse(message):
    text = getattr(message, "content", message)
    print(f"{text}")
    try:
        pattern2 = r"""
                    \{\s*
                    ['"]answer['"]\s*:\s*['"](?P<answer>.*?)['"]\s*,\s*
                    ['"]sources['"]\s*:\s*\[(?P<sources>.*?)\]\s*,\s*
                    ['"]language['"]\s*:\s*['"](?P<language>.*?)['"]\s*
                    \}
                    """



        match = re.search(pattern2, text)
        if match:
            answer = match.group("answer")
            src = match.group("sources")
            src = re.split(r'[]', src)
            lan = match.group("language")
            return {"answer":  answer, "src": src, "language": lan}

    except Exception as exception:
        print("exception")
        print(message)

    print("no match")
    return parse2(message)


def parse2(message_or_text: Union[AIMessage, str]):
        

        ret = {}
        content = getattr(message_or_text, "content", message_or_text)

        # 1) Grab the first {...} block
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            raise OutputParserException("No JSON-like block found")
        snippet = m.group(0)

        # 2) Quick-clean common stray-escape:   \" is valid, but \' isn't in JSON
        #    So replace any \\' with just an apostrophe
        snippet = snippet.replace("\\'", "'")

        # 3) Try strict JSON
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            # 4) Try JSON5 (allows single quotes, trailing commas, comments…)
            try:
                data = json5.loads(snippet)
            except Exception:
                # 5) Final fallback: Python literal eval
                try:
                    data = ast.literal_eval(snippet)
                except Exception as e:
                    raise OutputParserException(f"All parsers failed: {e}")

        # 6) Sanitize & defaults
        ans = data.get("answer", "")
        if isinstance(ans, str):
            ans = ans.replace("\\", "")  # strip stray backslashes
        sources = data.get("src") or []
        lang = data.get("language", "")

        # 7) Pydantic validation
        try:
            return {"answer": ans, "src": sources, "language": lang}
        except Exception as e:
            raise OutputParserException(f"Schema validation error: {e}")



parser = RunnableLambda(lambda x: parse(x))



#############################################################################################################

system_prompt = """
    You will recieve an output from an llm, probably malformated.
    you task is to give a structured otput that will be shown to the user.
    Please correct any errors, specially from catalan, make sure that the personal and verbal times are correct.
    You are the assistant and are to service to the user
    All the execution is below.
    NOTE THAT YOU SHOULD OUTPUT A JSON OBJECT USING DOUBLE QUOTES (") DO NOT USE SINGLE QUOTES (''), to use double quotes inside a sentence use backslash \\"

    The output should be formatted as a JSON instance that conforms to the JSON schema below.

    As an example, for the schema {{ "properties": {{ "foo": {{ "title": "Foo", "description": "a list of strings", "type": "array", "items": {{ "type": "string" }} }} }} , "required": ["foo"] }}
    the object {{ "foo": ["bar", "baz"] }} is a well-formatted instance of the schema. The object {{ "properties": {{ "foo": ["bar", "baz"] }} }} is not well-formatted. The object {{ 'foo': ['bar', 'baz'] }} is not well-formatted.
    
    Here is the output schema:

{{"properties": {{"answer": {{"description": " the answer to the question with NO BACKSLASHES, or a friendly response if no information is found with NO BACKSLASHES", "title": "Answer", "type": "string"}}, "src": {{"description": "list of urls in string format from where the information is extracted", "items": {{}}, "title": "Src", "type": "array"}}, "language": {{"description": "the language used i should be either ca es or en for catalan spanish or english", "title": "Language", "type": "string"}}}}, "required": ["answer", "src", "language"]}}

"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="scratchpad"),
    ("assistant", "Error message:{error_msg}"),
    
])

llm = get_llm()


llm_answer_parser = (
    {
        "input": lambda x: x["input"],
        "chat_history": lambda x: x["chat_history"],
        "scratchpad": lambda x: x.get("scratchpad", []),
        "error_msg": lambda x: x.get("error_msg", "No errors")
    }
    | prompt
    | llm
    | parser
   
)


