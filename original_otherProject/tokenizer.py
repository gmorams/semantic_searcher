import spacy
from utils import SingletonMeta

class Tokenizer(metaclass=SingletonMeta):
    def __init__(self):
        """
        Initializes the tokenizer by loading the spaCy models for Catalan, English, and Spanish.
        The default language is set to Catalan.
        """
        # Mapping of language codes to their respective spaCy model names.
        model_mapping = {
            "ca": "ca_core_news_sm",
            "en": "en_core_web_sm",
            "es": "es_core_news_sm"
        }
        self.nlp_models = {}
        for lang, model_name in model_mapping.items():
            try:
                self.nlp_models[lang] = spacy.load(model_name)
                print(f"Loaded model for {lang}: {model_name}")
            except Exception as e:
                print(f"Error loading model for language '{lang}' with model '{model_name}': {e}")

        # Ensure the default Catalan model is loaded
        if "ca" not in self.nlp_models:
            raise RuntimeError("Catalan model (ca_core_news_sm) is required and was not loaded.")

    def tokenize_text(self, text, lang):
        """
        Tokenizes the text based on its language.

        Parameters:
            - text: a string containing the text to tokenize.
            - lang: (e.g., "ca", "en", or "es").

        Returns:
            list: A list of token strings.
        """

        nlp = self.nlp_models.get(lang, self.nlp_models["ca"])
        doc = nlp(text)
        return str([token.lemma_ for token in doc])