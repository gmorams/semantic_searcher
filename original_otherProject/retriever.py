from retrieve.tree_and_tags import Tree_and_Tags
from retrieve.document_retriever import DocumentRetriever
from processing.tokenizer import Tokenizer
from chatbot.llm_tags_retrieve import select_tags
from processing.embedder import Embedder
from utils import measure_time, SingletonMeta


class Retriever(metaclass=SingletonMeta):

    @measure_time
    def __init__(self, tree:Tree_and_Tags, tokenizer: Tokenizer, embedder:Embedder):
            self.tree = tree
            self.tokenizer = tokenizer
            self.embedder = embedder

    def process_and_search(self, query, lan="ca"):
        if lan not in ["ca", "es", "en"]:
            lan = "ca"


        document_retriever = DocumentRetriever(k=3, tokenizer=self.tokenizer, embedder=self.embedder)


        print(f"Fent consulta: {query}  ________________________")

        docs = document_retriever.weighted_search_text(query, query, "ca")
        print(len(docs))

        docs2 = document_retriever.similarity_search_embeddings(query, [lan])

        print(f"s'han trobat {len(docs2)} documents ________________________")
        return docs
         
    def process_and_search_llm(self, query, lan="ca"):


        if lan not in ["ca", "es", "en"]:
            lan = "ca"

        tree_and_tags = Tree_and_Tags()
        tree_str = tree_and_tags.get_partial_tree_json(lan)

        print(f"_________________ Selecting tags for: {query}  _________________")



        tags, title, enriched_query = select_tags(query, "", tree_str)
        if lan not in tags:
            tags.append(lan)

        

        
        print(f"______________ Tags: {tags}  _________________")
        

        document_retriever = DocumentRetriever(k=3, tokenizer=self.tokenizer, embedder=self.embedder)


        if title and enriched_query:
            print("Performing Text BM25 search")
            docs = document_retriever.weighted_search_text(title, enriched_query , lan)
        else:
            print("Performing embbedding search")
            docs = document_retriever.similarity_search_embeddings(query, tags)


        print(docs)
        return docs




from langchain_openai import ChatOpenAI
from langchain.agents import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from chatbot.llm import get_llm

def get_tree_path_from_query(query : str, lan: str, tree:Tree_and_Tags) -> str :

    llm = get_llm(max_tokens=200)
    @tool
    def list_childs(path: str):
        """It shows the childs of mentioned node"""

        return tree.get_child_nodes(path)

    tools = [list_childs]

    template='Find the path most related for the users questions, its a tree jerarquic structure, you are on the root (empty string) and you can explore it. You dont have to get to the leafs, you can output a path of a parent. Output the final path. You have access to the following tools:\n\n{tools}\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the path found\n\nBegin!\n\nQuestion: {input}\nThought:{agent_scratchpad}'

    prompt_template = PromptTemplate.from_template(template)

    agent = create_react_agent(llm, tools, prompt_template)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    path = agent_executor.invoke({"input": f"{query} , language: {lan}"})

    return path['output']


def get_language(query):

    llm = get_llm()
    template = "Identify the language used by the user, and output ca if its catalan es if its spanish and en if its english. If you are unsure use catalan, only ouput ca or es or en. Here is the question or query: {query}"
    prompt_template = PromptTemplate.from_template(template)

    chain = prompt_template | llm

    return chain.invoke(query).content

