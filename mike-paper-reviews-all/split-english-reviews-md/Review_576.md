Review 576: From World Cup Statistics to Business Data: AI21's New RAG

From World Cup Statistics to Business Data: AI21's New RAG

Shmulik and Mike’s Daily Paper Review 09.02.26Structured RAG for Answering Aggregative Questions

The paper we are reviewing today was recently published by AI21 Labs, presenting an innovative approach to using RAG designed to solve one of the toughest problems in the field: answering aggregative questions over a collection of documents.

Before we dive into the architecture, let's look at an example. Suppose you are real estate moguls and you have a vast collection of documents such as contracts, specifications, and emails describing the properties you own. You want to ask questions in natural language like: "In which city do I have the most properties?", "What is the average price of a house I own?", "How many of my houses have a pool?", or "How many apartments have I purchased in the last 5 years?".

The initial instinct is to use the classic RAG-based solution. Unfortunately, standard RAG, which is based on vector search, will likely fail miserably on these questions for three main reasons:

Completeness Constraint: The retrieval mechanism pulls out the number of chunks most similar to the question. If you have 100 properties and you ask about an average, the system will only retrieve some of the documents. The average will be calculated based on a partial sample only, and the answer will be mathematically incorrect.

Context Constraint: Even if you try to push all documents into the context, you might exceed the model's maximum window. Furthermore, the model receives a lot of noise and unnecessary text when it only needed a single data point from each document.

Filtering Difficulty: Embedding models (used to identify relevant chunks or documents for a query) struggle significantly with precise logical constraints. It is difficult for them to distinguish between times or filter numbers reliably based solely on semantic similarity.

To address these issues, the paper proposes the S-RAG approach. The core idea is a paradigm shift: instead of "Retrieve and Read," the system performs "Structure and Query."

How does it work?

The solution consists of 3 main stages: the pre-processing stage (which happens once in advance) and the querying stage (which happens in real-time).

Schema Prediction: The system samples a small number of documents and representative questions from the corpus. Using an LLM, the system automatically infers a schema describing the entities in the documents. For example, for real estate documents, the system will understand it needs to create a schema with fields like city, price, existence of a pool, and purchase date. This stage turns unstructured information into an organized and defined schema.

Record Prediction and Canonicalization: This is the heart of the system. The model goes through all documents in the corpus and extracts from them the values corresponding to the schema we created. The critical part here is canonicalization: the model knows how to translate different formulations into a uniform format. For example, if in one document the number is written in shorthand (1M) and in another in full words, all will be saved in the database as a uniform number. The result is stored in a table in a relational DB.

Real-time Querying: When the user asks a question, the system does not search for similar texts. Instead, the model translates the question into a SQL query. The query runs on the database we created and returns a deterministic and accurate answer. The huge advantage is that the model does not need to calculate averages—the SQL engine does the math, and the model only formulates the final answer for the user.

I recommend looking at the attached image to understand this visually.

Methodology and Datasets

To examine aggregative questions (which require summation and data calculation), AI21 researchers used three datasets:

Hotels (Fully Synthetic): 350 invented hotel pages and 193 questions. The challenge: The model must rely 100% on the text without prior knowledge.

World Cup (Semi-Synthetic): 22 Wikipedia pages. Summary tables were removed to force the model to perform calculations from the text (such as summing goals).

FinanceBench (Real World): A public financial benchmark. 50 aggregative questions were tested as well as the full database.

Methodological Separation: Schema construction (Calibration) was performed on a small sample (12 documents), which was subsequently excluded from the test set to prevent bias.

Performance Comparison (Recall)

The following table summarizes the models' ability to return a full and accurate answer:

Dataset

Vector RAG

S-RAG (Auto Schema)

S-RAG (Manual Schema)

Hotels

Low

High

Very High

World Cup

Moderate

High

High

FinanceBench

Moderate

Low (due to errors)

High

The Advantage of S-RAG: In complex synthetic data (Hotels), S-RAG showed a dramatic improvement over vector RAG.

Importance of Schema Accuracy: The gap between automatic and manual schemas emphasizes that the quality of field definitions is critical to the system's success.

Pragmatic Solution: The solution they offer is pragmatic: investing just a few hours in refining the schema by a human can significantly improve results. The process does not require writing code from scratch, but rather better prompting and result verification.

Example: In FinanceBench, the automatic model collapsed due to standardization errors (e.g., confusing millions and billions), leading to incorrect SQL queries. A manual schema solved this.

Hybrid Approach: In the full FinanceBench containing both aggregative and regular questions, a combination of SQL for filtering and regular RAG for results achieved 0.667 (compared to 0.598 in vector RAG).

Summary

The paper demonstrates how using S-RAG, while adhering to a methodology of building a schema on a separate set or manual schema construction, solves the fundamental problems of RAG in computational and complex questions. The transition from textual search to structured search allows for precision and answers to questions that cannot be solved with standard RAG methods.

Shmulik’s Perspective

A few weeks ago, I was at an AI Tinkerers Meetup where AI21 presented the paper. Right from the start, I was really enthusiastic; I'm not a fan of RAG, and this method showed how you can integrate the schematic element to turn it into something completely different. Afterward, I went to read the paper, and the potential became even clearer to me, but one thing was missing—the code.

I like to try things with my own hands to see how they work, so I reconstructed the paper, and you can try it yourself in Google Colab: Structured Retrieval Augmented Generation.

The implementation is likely not identical to the original, but overall it's quite similar. Looking forward to talking with AI21 to understand the differences :)

https://arxiv.org/abs/2511.08505