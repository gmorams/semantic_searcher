from .response_parser import ResponseParser
from db.elastic_store import ElasticStore
from processing.tokenizer import Tokenizer
from processing.embedder import Embedder
import time
from datetime import datetime
import os

class DataPreprocessing():

    def parse_and_store_docs(self, response, url):
        """rep una response i el url, guarda a elastic la informacio parsejada"""
        try:
            response_parser = ResponseParser()
            docs = response_parser.parse(response, url)

            elastic_store = ElasticStore()
            doc_uuids = elastic_store.index_documents(docs)

            return doc_uuids

        except:
            print(f"ERROR parsing/indexing {url}")

    def parse_and_store_docs_parents(self, response, url, parents):
        """rep una response i el url, guarda a elastic la informacio parsejada"""
        try:
            response_parser = ResponseParser()
            docs = response_parser.parse(response, url, parents=parents)

            elastic_store = ElasticStore()
            doc_uuids = elastic_store.index_documents(docs)

            return doc_uuids

        except:
            print(f"ERROR parsing/indexing {url}")
            

    def _generate_chunks_to_embed(self, text, chunk_size=800):
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


    def tokenize_and_embed_db_content(self):
        """Itera sobre tots els documents de l'elastic, genera la versio tokenitzada del content i la guarda"""

        elastic_store = ElasticStore()
        tokenizer = Tokenizer()
        embedder = Embedder()

        scroll_id, hits, total_docs = elastic_store.start_scrolling()

        time1 = time.time()
        avg_interval = None

        docs_processed = 0
        
        while hits:
            for hit in hits:
                doc_id = hit['_id']
                doc = hit['_source']

                docs_processed += 1
                if "content" in doc.keys() and 'title' in doc.keys():

                    try:
                        if docs_processed%100 == 0:

                            interval = time.time() - time1
                            if avg_interval:
                                avg_interval = (avg_interval + interval)/2
                            else:
                                avg_interval = interval

                            time_left = ((total_docs - docs_processed)/100)*avg_interval    
                            minutes, seconds = divmod(time_left, 60)
                            seconds = int(seconds)
                            final_time = datetime.fromtimestamp(time.time() + time_left).strftime("%H:%M")

                            print(f"Processing {docs_processed}/{total_docs}   Aprox time left : {minutes}m {seconds}s      Final time: {final_time}", flush=True)
                            time1 = time.time()


        
                        if "content_tokenized" not in doc.keys() and "title_tokenized" not in doc.keys():

                            content_tok = tokenizer.tokenize_text(doc["content"], doc["lang"])
                            

                            title_tok = tokenizer.tokenize_text(doc["title"], doc["lang"])
                            


                            elastic_store.update_document(doc_id, content_tok, title_tok)



                        # embeddings

                        chunks_to_embed = self._generate_chunks_to_embed(doc["content"])
                        embedded = []
                        for to_embed in chunks_to_embed:
                           embedded.append(embedder.embed2(to_embed))

                        elastic_store.index_embeddings_bulk(doc_id, embedded, doc["tags"])


                    except Exception as e:
                        print(f"ERROR parsing {doc_id}")
                        print(e)


            scroll_id, hits = elastic_store.scroll(scroll_id)