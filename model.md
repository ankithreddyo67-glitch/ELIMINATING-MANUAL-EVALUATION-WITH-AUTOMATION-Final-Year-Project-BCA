# Model

Features capture reference token recall, answer token precision, rubric concept coverage, bigram overlap, length similarity, and negation mismatch. A sigmoid converts the weighted sum into a score fraction. Batch gradient descent fits soft marks targets using logistic loss and L2 regularization. The model uses lexical evidence and can miss semantic equivalence.
