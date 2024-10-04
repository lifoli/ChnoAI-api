from operator import not_
import os
import re

from tabnanny import check
from certifi import contents
from dotenv import load_dotenv
load_dotenv()

# langchin
from langchain_upstage import ChatUpstage, UpstageEmbeddings
from langchain_core.messages import HumanMessage
from typing import Annotated

# langfuse
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler()
langfuse = Langfuse()

from utils import (
    format_message, 
    load_conversation, 
    q_and_a,
    GraphState
)
from ..test_messages import fetch_messages

class SubtitleGenerator():
    def __init__(self, model="solar-pro", embedding_model = "solar-embedding-1-large"):
        self.model = ChatUpstage(model=model)
        self.embedding_model = UpstageEmbeddings(model = embedding_model)
        self.length_limit = 5000 # question character length limit

    # Generate an subtitle for a single QA pair.
    def generate_single_subtitle(self, question, answer):
        subtitle_generation : Annotated[str, HumanMessage] = langfuse.get_prompt("subtitle_generator")
        prompt = subtitle_generation.compile(question = question, answer=answer)
        response = self.model.invoke(prompt)
        return response.content.strip()
    
    def _get_sentence_embedding(self, sentence):
        """
        Computes the sentence embedding(s) for a given input.
        Args:
            sentence (str or list of str): The sentence or list of sentences to compute embeddings for. 
                                           If a list is provided, each sentence will be processed separately.
        Returns:
            list: A list of embeddings, each with a dimensionality of 4096.
        Raises:
            ValueError: If the input is neither a string nor a list of strings.
        """
        result = []
        if isinstance(sentence, list) and all(isinstance(item, str) for item in sentence):
            result = self.embedding_model.embed_documents(sentence)
        elif isinstance(sentence, str):
            result.append(self.embedding_model.embed_query(sentence))
        else:
            raise ValueError("input type must be str or list of str.")
        return result

    # main function
    def generate(self, chat_name = 'chat_ex2'):
        """
        Generates a list of subtitlees for question-answer (QA) pairs in a conversation.

        This method performs the following steps:
        1. Loads and formats conversation data from the specified chat file.
        2. Iterates through each QA pair in the conversation:
        - Trims questions and answers if they exceed the specified length limit.
        - Generates a unique subtitle for each QA pair and appends it to an subtitle list.
        3. Checks for consecutive duplicate subtitlees:
        - If two consecutive subtitlees are duplicates, the first subtitle is set to None,
            and the second subtitle is updated to reflect the non-duplicated version.
        4. Returns the list of subtitlees with duplicate entries handled.

        Args:
            chat_name (str): The name of the chat file to load and process. Default is 'chat_ex2'.

        Returns:
            list: A list of subtitlees generated for the QA pairs, with duplicates handled.
        """
         
        subtitle_list = []

        conversation_data = load_conversation(chat_name=chat_name)
        conversation_data = format_message(conversation_data)

        # generate subtitlees per each QA pairs 
        for idx, (_) in enumerate(conversation_data):
            conversation = conversation_data[idx]
            
            # Trim if the conversations are too long
            if (len(conversation['q']) > self.length_limit):
                conversation['q'] = conversation['q'][:self.length_limit]
            if (len(conversation['a']) > self.length_limit):
                conversation['a'] = conversation['a'][:self.length_limit]

            # Generate a subtitle per each QA pairs 
            subtitle_result = self.generate_single_subtitle(conversation['q'], conversation['a'])
            subtitle_list.append(subtitle_result)

        return subtitle_list

# Demo for debugging purpose
if __name__ == '__main__':
    CONVERSATION_ID_EXAMPLE_1 = 146
    CONVERSATION_ID_EXAMPLE_2 = 152
    result = fetch_messages(CONVERSATION_ID_EXAMPLE_1)
    print (result)
    #test = SubtitleGenerator()
    #subtitle_list = test.generate()
    #print(subtitle_list)