import re
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from deepeval.metrics import SummarizationMetric
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

##To discuss : 비교 대상, 혹은 점수 기준. 만약 일정 점수 이상 넘지 못하면 다시 generate 하는걸로?


def evaluate_bleu(reference, hypothesis):
    """Evaluates BLEU score between reference and hypothesis."""
    reference_tokens = reference.split()
    hypothesis_tokens = hypothesis.split()

    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], hypothesis_tokens, smoothing_function=smoothie)
    return score

def evaluate_rouge(reference, hypothesis):
    """Evaluates ROUGE scores between reference and hypothesis."""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return scores

def evaluate_recall(reference, hypothesis):
    """Computes recall as overlap of n-grams between reference and hypothesis."""
    ref_ngrams = set(reference.split())
    hyp_ngrams = set(hypothesis.split())
    if len(ref_ngrams) == 0:
        return 0.0
    recall = len(ref_ngrams & hyp_ngrams) / len(ref_ngrams)
    return recall

def evaluate_processed_answer(original_answer, processed_answer):
    """Evaluates BLEU, ROUGE, and recall scores between the original and processed answer."""
    bleu_score = evaluate_bleu(original_answer, processed_answer)
    rouge_scores = evaluate_rouge(original_answer, processed_answer)
    recall_score = evaluate_recall(original_answer, processed_answer)

    #print(f"BLEU Score: {bleu_score:.4f}")
    #print(f"ROUGE Scores: {rouge_scores}")
    #print(f"Recall Score: {recall_score:.4f}")

    return {
        "bleu": bleu_score,
        "rouge": rouge_scores,
        "recall": recall_score
    }
def evaluate_coherence(original_question, summarized_question):
    """Evaluates the quality of the summarization using GEval Coherence."""
    if not original_question or not summarized_question:
        print("Invalid input for summarization. Original or summarized question is empty.")
        return {
            "coherence_score": None,
            "reason": "Invalid input: Empty question or summarized question"
        }


    test_case = LLMTestCase(input=original_question, actual_output=summarized_question)
    
    coherence_metric = GEval(
        name="Coherence",
        criteria="Coherence - determine if the actual output is coherent with the input, and summarizes the input text correctly.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        strict_mode=False,  
        verbose_mode=False,
        model="gpt-4o-mini"   
    )
    coherence_metric.measure(test_case)
    #print(coherence_metric.score)
    #print(coherence_metric.reason)
    return{
        "coherence_score" : coherence_metric.score,
        "reason" :coherence_metric.reason
    }










#########################################
from deepeval import assert_test

def evaluate_summarization(original_question, summarized_question):
    test_case = LLMTestCase(input=original_question, actual_output=summarized_question)
    summarization_metric = SummarizationMetric(threshold=0.2, strict_mode=False, verbose_mode=True, model="gpt-4o-mini" )
    #result = summarization_metric.measure(test_case)
    assert_test(
        test_case,
        [summarization_metric],
        # run_async=False
    )
    #print(a.score)
    #print(f"Summarization Reason: {result.reason}")
#########################################3
