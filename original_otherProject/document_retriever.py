from typing import List, Optional
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from db.elastic_store import ElasticStore
from processing.tokenizer import Tokenizer
from processing.embedder import Embedder
from retrieve.tree_and_tags import Tree_and_Tags
from langchain.schema.runnable import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from utils import measure_time

class DocumentRetriever():
    @measure_time
    def __init__(self, k: int, tokenizer: Tokenizer, embedder:Embedder):
        self.k = k
        self.tokenizer = tokenizer
        self.es = ElasticStore()
        self.embedder = embedder


    def similarity_search_embeddings(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        embedding_field: str = "embedding1024",
    ) -> List[str]:
        """
        Returns the top-k document IDs by cosine similarity over `embedding_field`,
        filtered so that *all* provided `tags` must be present on each embedding.
        """
        # 1️⃣ Embed the query
        query_vec = self.embedder.embed(query)

        # 2️⃣ Build an AND-style tag filter
        filter_clause = None
        if tags:
            # one term clause per tag ⇒ all must match
            must_terms = [{"term": {"tags": tag}} for tag in tags]
            filter_clause = {"bool": {"must": must_terms}}

        # 3️⃣ Build the k-NN + filter query
        #    num_candidates can be tuned; here we fetch up to 5×k before re-ranking
        knn_query = {
            "field": embedding_field,
            "query_vector": query_vec,
            "k": self.k,
            "num_candidates": self.k * 5,
        }
        if filter_clause:
            knn_query["filter"] = filter_clause

        #print(knn_query)
        # 4️⃣ Execute the search on the embeddings index
        hits = self.es.search_embedding_filter_knn(knn_query)
        #print(hits)
        # 5️⃣ Extract and return only the doc_ids
        doc_ids = [hit["_source"]["doc_id"] for hit in hits]
        docs = self.es.get_documents_from_doc_ids(doc_ids)
        return self.parse_docs_from_hits(docs)


    def weighted_search_text(
            self,
            title: str,
            text: str,
            lang: str,
            urls: Optional[List[str]] = None,
            tags: Optional[List[str]] = [],
        ) -> List[Document]:
            """
            Returns the top-k documents by BM25 over:
            - title_tokenized (boost 2x)
            - content_tokenized (default boost)
            Filters by src URLs and/or tags if provided.
            """
            # 1️⃣ Tokenize each input
            tokenized_title = self.tokenizer.tokenize_text(title, lang)
            tokenized_text  = self.tokenizer.tokenize_text(text,  lang)

            if lang not in tags:
                tags.append(lang)
                
            # 2️⃣ Build optional filters

            #print("text")
            #print(tokenized_text)
            #print("titol")
            #print(tokenized_title)

            #print("..")
            filters = []
            if urls:
                filters.append({"terms": {"src": urls}})
            if tags:
                filters.append({"terms": {"tags": tags}})

                # ——— change here ———
            should_clauses = [
                {
                    "match": {
                        "title_tokenized": {
                            "query": tokenized_title,
                            "boost": 2.0
                        }
                    }
                },
                {
                    "match": {
                        "content_tokenized": {
                            "query": tokenized_text,
                            "boost": 1.0
                        }
                    }
                }
            ]

            bool_query: dict = {
                "should": should_clauses,
                # ensure at least one of the fields matches:
                # (if you omit this, ES will default to minimum_should_match=1
                "minimum_should_match": 1
            }
            if filters:
                bool_query["filter"] = filters

            body = {"query": {"bool": bool_query}}

            print(body)
            hits = self.es.search_text(body)
            return self.parse_docs_from_hits(hits)
   
    def parse_docs_from_hits(self, hits):

        docs = [
            {
            "content": elem['_source']['content'],
            "src": elem['_source']['src'],
            "id": elem['_id'],
            "title":  elem['_source']['title'],
            "tags":  elem['_source']['tags']
            } for elem in hits
        ]
        return docs

        final_str = " " + "}{".join([" ".join([f"{field}:{cont}" for field, cont in doc.items()]) for doc in docs]) + "}"
        final_str = final_str[1::]
        return final_str

        
        docs = [
            Document(
                page_content=elem['_source']['content'], 
                metadata={
                    'src': elem['_source']['src'], 
                    'tree': elem['_source']['tree'], 
                    'id': elem['_id'], 
                }) for elem in hits]
        
        return docs


## unused

    def similarity_search_text_filters(self, query, lang, urls=None, tags=None):
        """
        Retorna una llista dels top_n documents que mes s'assemblen segons BM25
        sobre title_tokenized (boost 2x) i content_tokenized, filtrant per URLs
        i/o tags si se'ns passen.
        """
        # 1. Tokenize
        tokenized_q = self.tokenizer.tokenize_text(query, lang)

        # 2. Build filters
        filters = []
        if urls:
            filters.append({"terms": {"src": urls}})
        if tags:
            filters.append({"terms": {"tags": tags}})

        # 3. Build the bool query
        bool_q = {
            "must": {
                "multi_match": {
                    "query":  tokenized_q,
                    "fields": [
                        "title_tokenized^2",   # give title twice the weight
                        "content_tokenized"    # default weight
                    ]
                }
            }
        }
        if filters:
            bool_q["filter"] = filters

        body = {"query": {"bool": bool_q}}

        # 4. Execute and parse
        elastic_store = ElasticStore()
        hits = elastic_store.search_text(body)
        docs = self.parse_docs_from_hits(hits)

        print(f"Found {len(docs)} documents matching text + filters")
        return docs

    def similarity_search_embeddings_not_efficient(
        self,
        query: str,
        urls: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        embedding_field: str = "embedding1024",
    ) -> List[Document]:
        """
        Returns the top-k documents by cosine similarity over `embedding_field`,
        but only after filtering by `src` URLs and/or `tags`.
        """
        # 1️⃣ Embed the query
        embedder = Embedder()
        query_vec = embedder.embed(query)

        # 2️⃣ Build filter for docs
        filters = []
        if urls:
            filters.append({"terms": {"src": urls}})
        if tags:
            filters.append({"terms": {"tags": tags}})

        doc_filter_body = {"query": {"bool": {}}}
        if filters:
            doc_filter_body["query"]["bool"]["filter"] = filters

        # 3️⃣ Get candidate doc hits and extract IDs
        es = ElasticStore()
        doc_hits = es.search_docs(doc_filter_body, size=10000)
        if not doc_hits:
            return []
        candidate_ids = [hit["_id"] for hit in doc_hits]

        # 4️⃣ k-NN search restricted by doc_id on embeddings index
        num_candidates = len(candidate_ids)
        k = min(self.k, num_candidates)
        knn_query = {
            "field":         embedding_field,
            "query_vector":  query_vec,
            "k":             k,
            "num_candidates": num_candidates,
            "filter": {
                "terms": {"doc_id": candidate_ids}
            }
        }
        knn_hits = es.search_embedding_filter_knn(knn_query)

        # 5️⃣ Fetch the actual docs and parse
        emb_doc_ids = [hit["_source"]["doc_id"] for hit in knn_hits]
        doc_hits = es.mget_documents(emb_doc_ids)
        return self.parse_docs_from_hits(doc_hits)
    #def get_relevant_documents(self, query: str, lan: str, path: str) -> List[Document]:
    #    return self.similarity_search_filter_embeddings(query, path)
    