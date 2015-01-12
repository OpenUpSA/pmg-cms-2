from __future__ import division
import nltk


def levenshtein(first, second):
    """
    Return a similarity ratio of two pieces of text. 0 means the strings are not similar at all,
    1.0 means they're identical. This is the Levenshtein ratio:
      (lensum - ldist) / lensum
    where lensum is the sum of the length of the two strings and ldist is the
    Levenshtein distance (edit distance).
    See https://groups.google.com/forum/#!topic/nltk-users/u94RFDWbGyw
    """
    lensum = len(first) + len(second)
    ldist = nltk.edit_distance(first, second)

    if lensum == 0:
        return 0

    return (lensum - ldist) / lensum