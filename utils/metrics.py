from nltk.translate.bleu_score import sentence_bleu

def bleu_score(reference, candidate):
    score = sentence_bleu(reference, candidate)
    return score