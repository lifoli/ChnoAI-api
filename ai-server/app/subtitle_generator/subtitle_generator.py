from operator import not_
import os
import sys
import yaml

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances
from tqdm import tqdm

import logging

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    format_message, 
    fetch_messages
)
from db_client import get_db_client

class SubtitleGenerator():
    def __init__(self, config_path="subtitle_generator.yaml"):
        # Load configuration from YAML file
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Load configurations
        logging.info(f'Subtitle generator configuration: {config}')
        self.model = ChatUpstage(model=config.get('model'))
        self.embedding_model = UpstageEmbeddings(model=config.get('embedding_model'))
        self.length_limit = config.get('length_limit')  
        self.merge_strategy = config.get('merge_strategy')
        self.merge_cluster_num = config.get('merge_cluster_num')  
        self.debug = config.get('debug') 

    # Generate an subtitle for a single QA pair.
    def generate_subtitles(self, question, answer):
        subtitle_generation : Annotated[str, HumanMessage] = langfuse.get_prompt("subtitle_generator")
        prompt = subtitle_generation.compile(question = question, answer=answer)
        response = self.model.invoke(prompt)
        return response.content.strip()
    
    def _reorder_subtitles(self, subtitle_list,qa_index):
        """
        Renumbering and reordering so that the subtitle mentioned first has the previous index.
        """
        # Create the renumber mapping based on the first appearance of numbers in num_lists
        number_map = {}
        next_number = 0
        renumbered_qa_lists = []

        for sublist in qa_index:
            renumbered_sublist = []
            for num in sublist:
                if num not in number_map:
                    number_map[num] = next_number
                    next_number += 1
                renumbered_sublist.append(number_map[num])
            renumbered_qa_lists.append(renumbered_sublist)

        # Reorder the subtitle_list based on the renumber mapping
        reordered_subtitles = [None] * len(subtitle_list)

        # Fill the reordered_subtitles based on the mapping
        for i, _ in enumerate(reordered_subtitles):
            reordered_subtitles[i] = subtitle_list[number_map[i]]

        return reordered_subtitles, renumbered_qa_lists
    
    
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
    
    def _format_data(self, subtitle_list, qa_index_list):
        """
        format data to return to fit for writer
        """
        subtitle_dict = {}
        qa_index_dict = {}
        
        for idx, (subtitle) in enumerate(subtitle_list):
            subtitle = subtitle.replace('"', '')
            subtitle_dict[str(idx)] = f'## {idx}) {subtitle}'
        
        for idx, (qa_index) in enumerate(qa_index_list):
            qa_index_dict[str(idx)] = qa_index

        return subtitle_dict, qa_index_dict

    def merge_subtitle(self, subtitle_list):
        """
        Merges generated subtitles from each QA pair into a finite set of distinct subtitles.

        Args:
            subtitle_list (list(list(str))): A list of lists, where each inner list contains subtitles generated for a QA pair.

        Returns:
            subtitles (list(str)): A merged list of distinct subtitles.
            subtitle_index (list(list(int))): A list of lists, where each inner list indicates the index of the subtitle corresponding to each QA pair.
        """
        logging.info(f'merging start. merging strategy: {self.merge_strategy}')

        result = []

        if self.merge_strategy == 'llm':
            raise NotImplementedError()
        
        elif self.merge_strategy == 'embedding':
            
            subtitle_embedding_list = [] # list(list(float)): each subtitle embeddings
            subtitle_embedding_numpy = [] # list(float) -> np.array: np array to calculate kMeans
            subtitle_index = [] # list(list(int)) Index to which the subtitle belongs

            # Calculate embeddings of subtitles
            for subtitles in subtitle_list:
                subtitle_embedding = self._get_sentence_embedding(subtitles)
                subtitle_embedding_list.append(subtitle_embedding)
            
            # concatenate all subtitle embedding lists into one list to make it as numpy vector
            for subtitle_embedding in subtitle_embedding_list:
                subtitle_embedding_numpy.extend(subtitle_embedding)
            subtitle_embedding_numpy = np.array(subtitle_embedding_numpy) # (N, 4096)

            # Ensure the number of clusters does not exceed the number of data points
            n_samples = subtitle_embedding_numpy.shape[0]  # 데이터 포인트의 개수
            n_clusters = min(n_samples, self.merge_cluster_num)  # 클러스터 수가 샘플 수를 초과하지 않도록 조정
            
            # Cluster the embeddings using KMeans
            logging.info('Start calculating kMeans...')
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            kmeans.fit(subtitle_embedding_numpy)

            # Compute the Euclidean distance between the given embedding and each cluster center
            logging.info('Find closest kMean point for each subtitle embeddings...')
            for subtitle_embedding in subtitle_embedding_list:
                subtitle_index_sublist = []
                for subtitle_single_embedding in subtitle_embedding:
                    distances = euclidean_distances([subtitle_single_embedding], kmeans.cluster_centers_)
                    subtitle_index_sublist.append(np.argmin(distances))
                subtitle_index.append(subtitle_index_sublist)
            if self.debug:
                print(subtitle_index)
            
            # Sum up subtitles with same clusters and merge them into a single subtitle with an LLM 
            subtitle_clustered = [[] for _ in range(n_clusters)]
            for i, (subtitles) in enumerate(subtitle_list):
                for j, (single_subtitle) in enumerate(subtitles):
                    subtitle_clustered[subtitle_index[i][j]].append(single_subtitle)
            if self.debug:
                print(subtitle_clustered)

            logging.info(f'Merging subtitles into {n_clusters} subtitle...')
            for i in range(n_clusters):
                subtitle_merge_prompt : Annotated[str, HumanMessage] = langfuse.get_prompt("subtitle_generator_merge")
                prompt = subtitle_merge_prompt.compile(subtitles=str(subtitle_clustered[i]))
                response = self.model.invoke(prompt)
                result.append(response.content.strip())

            if self.debug:
                print(result, [sorted(set(sublist)) for sublist in subtitle_index])
                
            return result, [sorted(set(sublist)) for sublist in subtitle_index]

        else:
            raise ValueError("specified merge_strategy is invalid.")

    def generate(self, conversation):
         
        subtitle_list = []
        conversation_data = format_message(conversation)

        # generate subtitlees per each QA pairs 
        for idx, conversation in tqdm(enumerate(conversation_data), total=len(conversation_data), desc="Generating Subtitles"):
            conversation = conversation_data[idx]
            
            # Trim if the conversations are too long
            if (len(conversation['q']) > self.length_limit):
                conversation['q'] = conversation['q'][:self.length_limit]
            if (len(conversation['a']) > self.length_limit):
                conversation['a'] = conversation['a'][:self.length_limit]

            # Generate a subtitle per each QA pairs 
            subtitle_result = self.generate_subtitles(conversation['q'], conversation['a'])

            # parse the answer and make them into a list
            subtitle_result = subtitle_result.splitlines()
            subtitle_result = [line for line in subtitle_result if line.strip()] # remove if a line is empty

            if self.debug:
                tqdm.write(f"Processed subtitles for QA pair {idx + 1}: {subtitle_result}")

            #print('converted_subtitle', subtitle_result)
            subtitle_list.append(subtitle_result)
        logging.info('generating subtitles is done.')

        return subtitle_list
    
    def __call__(self, conversation):
        subtitle_list = self.generate(conversation)
        subtitle_list, qa_indices = self.merge_subtitle(subtitle_list)
        subtitle_list, qa_indices = self._reorder_subtitles(subtitle_list=subtitle_list,qa_index=qa_indices)
        return self._format_data(subtitle_list, qa_indices)

# Demo for debugging purpose
if __name__ == '__main__':
    database = get_db_client()
    CONVERSATION_ID_EXAMPLE_1 = 146
    CONVERSATION_ID_EXAMPLE_2 = 152
    conversation = fetch_messages(database, CONVERSATION_ID_EXAMPLE_2)
    print('current path:', os.getcwd())
    test = SubtitleGenerator(config_path="../configs/subtitle_generator.yaml")
    #subtitle_list = test.generate(conversation)
    #test.merge_subtitle(subtitle_list)
    print('result:',test(conversation))