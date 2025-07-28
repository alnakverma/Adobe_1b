# Technical Approach Explanation

This document provides a detailed explanation of the technical approach, design decisions, and architecture for the PDF Intelligence Engine solution.

## Overall Architecture

The solution is architected as an offline-first, containerized Python application. The key design principles were:

*   **Portability and Reproducibility**: Using Docker ensures that the application runs in a consistent environment with all dependencies pre-installed, regardless of the host machine. The `Dockerfile` is configured to be built for `linux/amd64` architecture as required.
*   **Offline Capability**: All required models and libraries are included within the Docker image. The `--network none` flag can be used during execution to guarantee no external network calls are made.
*   **Flexibility**: A single entrypoint (`main.py`) is used for both rounds. The execution path is determined at runtime by the presence of the `ADOBE_QUERY` environment variable, which is a clean and standard way to configure container behavior.

---

## Round 1A: Outline Extraction - A Heuristic-Based Approach

For outline extraction, a heuristic-based method was chosen over more complex machine learning layout analysis models. This decision was based on the hackathon's constraints:

*   **Speed**: Heuristics are computationally inexpensive and extremely fast, which is critical for meeting the performance requirements.
*   **Simplicity**: The logic is straightforward to implement and debug.
*   **No Training Data**: This approach does not require any pre-labeled data for training.

### Detailed Heuristic Pipeline

1.  **Establish a Baseline (Body Text)**: The core idea is that headings are defined by how they *differ* from the main body text. The script first identifies the most frequent (mode) font size and font name across the entire document. This establishes a reliable baseline for what constitutes "normal" text.

2.  **Identify Heading Candidates**: Every text block is then compared against this baseline. A block is flagged as a potential heading if it meets a combination of criteria designed to filter out noise:
    *   **Size**: It must be larger than the body text.
    *   **Weight**: Its font name often includes a keyword like `Bold`.
    *   **Structure**: It is typically a short line of text and does not end with a period, distinguishing it from regular sentences.

3.  **Classify Title vs. Headings**: The document title is assumed to be the most prominent text element, so it's identified as the text with the largest font size appearing on the first page.

4.  **Determine Heading Hierarchy (H1, H2, ...)**: The hierarchy is derived directly from the font sizes of the identified headings. All unique heading font sizes are collected and sorted in descending order. The largest size is assigned to H1, the second largest to H2, and so on. This creates a robust and dynamic leveling system that adapts to the styling of each unique PDF.

### Limitations

This heuristic approach works well for a wide range of standard documents but may struggle with highly unconventional or graphically rich PDFs where text styling is not consistent.

---

## Round 1B: Persona-Driven Intelligence - A Two-Pass Semantic Search

Round 1B required a deeper understanding of the content's meaning across a collection of documents. To achieve this, a **two-pass semantic search** architecture was implemented. This approach allows the system to first identify the most relevant high-level sections and then zoom in to find the most salient, granular pieces of information within them.

### Model Selection: `all-MiniLM-L6-v2`

The choice of the NLP model was critical. The `all-MiniLM-L6-v2` model was selected for several reasons:

*   **Performance**: It offers excellent performance for semantic similarity tasks.
*   **Size**: At ~86MB, it is lightweight and well under the 1GB model size constraint.
*   **Efficiency**: It is fast enough to run on a CPU within the time limits, avoiding the need for a GPU.

### Pass 1: High-Level Section Ranking

The first pass is designed to identify the most relevant sections across the entire document collection.

1.  **Rich Query Formulation**: The `persona` and `job-to-be-done` inputs are combined into a single, rich query string. This provides the model with maximum context about the user's needs.

2.  **Section Extraction**: The system processes all PDFs in the collection and uses the same heading-based logic from Round 1A to group content into structured sections. Each section is tagged with its source document and page number.

3.  **Global Ranking**: All sections from all documents are put into a single pool. A semantic search is performed to calculate the cosine similarity between the rich query and each section. This produces a globally ranked list of the most relevant sections, regardless of which document they came from.

### Pass 2: Granular Sub-Section Analysis

The second pass is designed to fulfill the "Sub-section Analysis" requirement by drilling down into the most promising sections identified in Pass 1.

1.  **Content Chunking**: The system takes the content of the top N (e.g., top 5) sections from the first pass. This content is then broken down into smaller, more granular chunks. In this implementation, we split the text by newlines, effectively creating paragraphs or sub-paragraphs.

2.  **Re-Ranking**: These granular chunks are then put into a new pool, and the same semantic search is performed again, ranking them against the original rich query.

3.  **Final Output**: The result is a highly-refined list of the most relevant sentences or paragraphs from the most relevant sections of the document collection. This two-pass approach ensures that the final output is not just a list of relevant chapters, but a precise list of the exact text that matters most to the user.
