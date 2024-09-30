import re
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from deepeval.metrics import SummarizationMetric
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

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

    print(f"BLEU Score: {bleu_score:.4f}")
    print(f"ROUGE Scores: {rouge_scores}")
    print(f"Recall Score: {recall_score:.4f}")

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
        criteria="Coherence - the collective quality of all sentences in the actual output",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        strict_mode=False,  
        verbose_mode=True   
    )
    coherence_metric.measure(test_case)
    print(coherence_metric.score)
    print(coherence_metric.reason)


def evaluate_summarization(original_question, summarized_question):
    test_case = LLMTestCase(input=original_question, actual_output=summarized_question)
    summarization_metric = SummarizationMetric(threshold=0.2, strict_mode=False, verbose_mode=True)
    try:
        result = summarization_metric.measure(test_case)
        if result is None:
            print("Summarization metric failed to produce a result. Please check the input and summarization settings.")
            return {
                "coherence_score": None,
                "reason": "No result from SummarizationMetric"
            }

        print(f"Summarization Coherence Score: {result.score}")
        print(f"Summarization Reason: {result.reason}")
        
        return {
            "coherence_score": result.score,
            "reason": result.reason
        }
    except Exception as e:
        print(f"Error during summarization evaluation: {str(e)}")
        return {
            "coherence_score": None,
            "reason": str(e)
        }
