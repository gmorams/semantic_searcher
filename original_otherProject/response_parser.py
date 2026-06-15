from bs4 import BeautifulSoup
import re 
from io import BytesIO
import PyPDF2 
import fitz  # PyMuPDF

from langchain_core.documents import Document

class ResponseParser():

    def parse(self, response, url, parents=[]):
        """rep una response i el url de la response. La response pots ser un pdf o una pagina web"""
        
        docs = []

        if ".pdf" in url:
            docs = self.parse_pdf(response, url)
        else:
            docs = self.parse_web(response, url)
        #NO aqui els docs ja tenen page_content, metadata["title1"], metadata["title2"]
        #SI aqui els docs ja tenen page_content, metadata["title"]

        parent_tags = set()
        for parent_url in parents:
            parent_tags.add(parent_url.removeprefix("https://www.fib.upc.edu/").strip().split("/"))

        

        for i in range(len(docs)):
            docs[i].metadata["src"] = url
            docs[i].metadata["tree"] = url.removeprefix("https://www.fib.upc.edu/")
            docs[i].metadata["lang"] = docs[i].metadata["tree"][0:2]
            docs[i].metadata["tags"] = url.removeprefix("https://www.fib.upc.edu/").strip().split("/") + list(parent_tags)
            docs[i].metadata["title"] = docs[i].metadata["title"]


        return docs

    #### PDF PARSING ###

    def get_title1_pdf(self, pdf_content):
        """
        Extracts the title based on the largest font size on the first page.
        Groups consecutive lines with the largest font size as part of the title.
        """
        doc = fitz.open(stream=pdf_content, filetype="pdf")

        for page in doc:  # Process only the first page
            blocks = page.get_text("dict")["blocks"]  # Get text blocks

            # Store spans with their font sizes
            spans_with_sizes = []

            for block in blocks:
                if "lines" in block.keys():
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                spans_with_sizes.append((span["size"], span["text"].strip()))

            # Find the largest font size
            if not spans_with_sizes:
                return "No title found"

            max_font_size = max(spans_with_sizes, key=lambda x: x[0])[0]

            # Collect all spans with the largest font size
            largest_text_spans = [
                text for size, text in spans_with_sizes if abs(size - max_font_size) < 1.0
            ]

            # Return the grouped title as a single string
            if largest_text_spans:
                return " ".join(largest_text_spans)

        return ""

    def get_title2_pdf(self, text):
        """
        gets the text with titles as <heading My title>
        returns the title and also the text without the <heading > tags to locate titles
        """

        pattern = r'<heading\s+([^>]*)>'
        text_titles = re.findall(pattern, text)

        title = " ".join(text_titles)

        cleaned_text = re.sub(pattern, r'\1', text)

        return title[:300], cleaned_text

    def remove_header_and_page_nums_pdf(self, s):
            """
            rep un string d'una pagina de pdf, treu la primera linia que es el header,
            i tambe treu el numero de pagina suposant que es troba a la segona linia,
            retorna el mateix string modificat
            """

            s = s.strip() #treiem espais 
            
            #treiem la primera linia 
            count = 0
            for ch in s:
                if ch == '\n':
                    break 
                count += 1
            
            s = s[count::]

            s = s.strip() #treiem espais  

            # A la segona linia hi ha el numero de pagina, el treiem amb la regex:
            segona_linia = s.split("\n")[0]
            x = re.search("(\r|\s)*[0-9]+.*", segona_linia)
            if x:
                x2 = re.search("[0-9]+", segona_linia)
                if x2:
                    _, pos2 = x2.span()
                    s = s[pos2:]

            s = s.strip()
            return s

    def parse_pdf(self, response, url):
        """ rep la response d'un pdf, el llegeix i el separa en seccions, retorna la llista d'aquestes seccions en format [Document]"""
        pdf_content = BytesIO(response.content)
        try:
            title1 = self.get_title1_pdf(pdf_content)
        except:
            title1 = ""
            print(f"ERROR parsing title1 on {url}")
        reader = PyPDF2.PdfReader(pdf_content) 
        
        #extraiem tot el text del pdf a un string netejant els headers i numeros de pagin
        text = "" 
        for page_num in range(len(reader.pages)): 
                page = reader.pages[page_num] 
                text += "\n" + self.remove_header_and_page_nums_pdf(page.extract_text()) 

        
        pdf_text = text

        #Filtrem titols:

            #Titol que te mes de tres majuscules i acaba en una linia nova
            #Titol que comença amb un numero i despres conte almenys 3 lletres i acaba en linia nova i no en : ni en .
            #Titol que comença amb article i un numero i acaba en linia nova

        section_pattern = r'(?P<title>\n[A-ZÀ-ÿ\s]{3,}|.*(Article).[0-9]*.*|(\n|{.})[0-9]+.*[a-zA-ZÀ-ÿ\s]+)(\r)*\n'
        

        sections = [] 

        matches = list(re.finditer(section_pattern, pdf_text)) 
        

        for i, match in enumerate(matches): 

            title = match.group('title').strip() 

            #afegim les seccions de text fins el seguent titol, la ultima l afegim directament
            if i < len(matches) - 1: 
                section_text = pdf_text[match.end():matches[i + 1].start()].strip() 
            else: 
                section_text = pdf_text[match.end():].strip() 
            
            sections.append(f"<heading {title}> {section_text}") # d'aquesta manera encara que agrupem tindrem els titols de les seccions


        filtered_sections = []

        mida_text_petit = 300 # es la mida minima de text que quedara
        mida_text_gran = 1000  # es la mida a la qual no se li uniran mes textos si son petits


        for i, s in enumerate(sections):

            #si la seccio es molt curta l'afegim a l'anterior si l anterior no es molt gran o si la seguent es molt gran l afegim igual.

            if i == 0: # la primera la afegim
                filtered_sections.append(s)
            elif i == len(sections)-1: # la ultima fem el mateix que sempre pero sense comporvar el seguent
                if len(s) < mida_text_petit and len(filtered_sections[-1]) < mida_text_gran:
                    filtered_sections[-1] += "\n\n" + s
                else:
                    filtered_sections.append(s)
            else:
                if len(s) < mida_text_petit and (len(filtered_sections[-1]) < mida_text_gran or len(sections[i+1]) > mida_text_petit):
                    filtered_sections[-1] += "\n\n" + s
                else:
                    filtered_sections.append(s)

        documents = []
        for section in filtered_sections:
            #title1 esta definit al principi
            title2, cleaned_section = self.get_title2_pdf(section)
            documents.append( Document(
                page_content = cleaned_section,
                metadata = 
                {
                    "title1": title1,
                    "title2": title2,
                }
            )
            )
            
        return documents

        



    #### WEB PARSING ###
    def get_title_web(self, text, url):
        """
        gets the text and url and returns the title (this is for search pourpuses)
        return s the title and also the text without the <heading > tags to locate titles
        """


        #url tags
        url_title = ""
        url_list = url.strip().split("/")
        if len(url_list) >=4:
            url_list = url_list[4:]
            url_list = [url_elem.replace("-", " ") for url_elem in url_list]
            url_str= " ".join(url_list)
            url_set = set(url_str.split(" "))
            url_title = " ".join(url_set) #elimina les paraules repetides

        #text
        pattern = r'<heading\s+([^>]+)>'
        text_titles = re.findall(pattern, text)
        text_title = " ".join(text_titles)
        title = text_title + " " + url_title
        cleaned_text = re.sub(pattern, r'\1', text)

        
        return title, cleaned_text

    def extract_sections_web(self, text): # nomes s'utilitza en els casos en que parse_web() no retorna res o gariebe res
        """
        rep un text i el separa en seccions, retorna una llista de seccions
        """

        #Titol que te mes de tres majuscules i acaba en una linia nova
        #Titol que comença amb un numero i despres conte almenys 3 lletres i acaba en linia nova i no en : ni en .

        section_pattern = r'(?P<title>\n[A-ZÀ-ÿ\s]{3,}|.*(Article).[0-9]*.*)'

        sections = [] 

        matches = list(re.finditer(section_pattern, text)) 
        

        for i, match in enumerate(matches): 

            title = match.group('title').strip() 

            #afegim les seccions de text fins el seguent titol, la ultima l afegim directament
            if i < len(matches) - 1: 
                section_text = text[match.end():matches[i + 1].start()].strip() 
            else: 
                section_text = text[match.end():].strip() 

            
            sections.append(f"{title}{section_text}") 


        #les seccions massa grans les partim

        #sections = self.partir_seccions_massa_grans(sections)


        filtered_sections = []

        mida_text_petit = 1000 # es la mida minima de text que quedara
        mida_text_gran = 3500  # es la mida a la qual no se li uniran mes textos si son petits


        for i, s in enumerate(sections):

            #si la seccio es molt curta l'afegim a l'anterior si l anterior no es molt gran o si la seguent es molt gran l afegim igual.

            if i == 0: # la primera la afegim
                filtered_sections.append(s)
            elif i == len(sections)-1: # la ultima fem el mateix que sempre pero sense comporvar el seguent
                if len(s) < mida_text_petit and len(filtered_sections[-1]) < mida_text_gran:
                    filtered_sections[-1] += "\n\n" + s
                else:
                    filtered_sections.append(s)
            else:
                if len(s) < mida_text_petit:
                    if (len(filtered_sections[-1]) < mida_text_gran or len(sections[i+1]) > mida_text_petit):
                        filtered_sections[-1] += "\n\n" + s
                    else:
                        filtered_sections.append(s)
                else: #(la mida del text es mes rgan que la minima)
                    if len(filtered_sections[-1]) < mida_text_petit: # fem el append si la antiga es petita i no s'ha unit enlloc
                        filtered_sections[-1] += "\n\n" + s
                    else:
                        filtered_sections.append(s)

        return filtered_sections 
    
    def parse_web(self, response, url):

        soup = BeautifulSoup(response.content, 'html.parser')
        h1_titles = soup.find_all('h1')
        h1_titles = [t.text for t in h1_titles]

        html_content = soup.find('div', id="section-main-content")


        mida_min = 500

        tag = "h2"
        #generem les seccions a partir del html
        h2tags = html_content.find_all(tag)

        sections = []
        for heading in h2tags:
            sect = ""
            for sibling in heading.find_next_siblings():
                if sibling.name == tag:  
                    break
                sect += sibling.text

            sections.append(f"<heading {heading.text}> \n{sect}")


        #les seccions massa grans les partim (ara mateix no les partim)
        #sections = self.partir_seccions_massa_grans(sections)

        #si no hi ha sections no entrara al bucle i no petara per l'index
        grouped_sections = []
        if sections:
            grouped_sections = [sections[0]]


        # si una seccio es molt curta l'enganxem a la seccio de adalt amb la condicio que la anterio sigui petita o que la seguent sigui gran
        for i in range(1,len(sections)):
            prev_section = grouped_sections[-1]
            section = sections[i]
            next_section = "aa"*mida_min # si es la ultima iteracio next_section tindra mida = 2*mida_min i per tant si la ultima seccio es curta l'agefirem igualment a l'anterior
            if i+1 < len(sections):
                next_section = sections[i+1]
            
            if len(section) < mida_min:
                if len(prev_section) < mida_min:
                    grouped_sections[-1] += section
                elif len(next_section) > mida_min:
                    grouped_sections[-1] += section
                else: # la anterior es mes gran i la seguent es mes petita, es el cas en el que l'hem d'afegir directament sense juntarla
                    grouped_sections.append(section)
            else: #la seccio es gran
                if len(prev_section) < mida_min: # si la seccio anterior es petita la sumem a aquesta (aixo ho fem sobretot per a la primera seccio)
                    grouped_sections[-1] += section
                else:
                    grouped_sections.append(section)
                
        #si gairebe no hi ha text retornem el text passat pel filtre de partir string molt semblant al dels pdfs
        if not grouped_sections or (len(grouped_sections) == 1 and len(grouped_sections[0]) < 100):
            grouped_sections = self.extract_sections_web(html_content.get_text()) 


        #transformem les seccions a documents
        docs = []
        for section in grouped_sections:

            title2, section_cleaned = self.get_title_web(section, url) # els subtitols es troben en el text i aqui es retornen els titols i el text net
            title1 = " ".join(h1_titles) + " " + url.strip().split("/")[-1]

            docs.append(
                Document(
                    page_content = section_cleaned,
                    metadata={
                        "title": title1 + " " + title2,
                        #"title2": title2,
                    })
                )
            
        #print(".", end="")

        return docs