# Adobe Hackathon - PDF Intelligence Engine

This project is a solution for the Adobe Hackathon, designed to extract structured information from PDF documents and rank sections based on semantic relevance to a user's query.

## Approach

The solution is divided into two main rounds, each building upon the last.

### Round 1A: Outline Extraction

The primary goal of Round 1A is to extract a structured outline (Title and Headings) from a PDF document. The approach is based on a set of heuristics, as simply relying on font size is not always reliable.

1.  **Text Block Extraction**: The process begins by using the `PyMuPDF` (fitz) library to extract all text blocks from the PDF. Crucially, this extraction includes metadata for each text span, such as its font size, font name, and page number.

2.  **Body Text Identification**: To find headings, we first need a baseline for what constitutes normal body text. The script analyzes all extracted text blocks to find the most common (mode) font size and font name. This combination is assumed to be the standard style for paragraph text.

3.  **Heading Detection Heuristics**: Any text block that deviates from the body text style is considered a potential heading. The following rules are applied:
    *   **Font Size**: Must be larger than the body text font size.
    *   **Font Weight**: The font name contains "Bold" (a common indicator).
    *   **Line Length**: The line is short (headings are typically not long sentences).
    *   **Punctuation**: The line does not end with a period.

4.  **Title and Heading Classification**: The document's title is identified as the text with the largest font size on the first page. The remaining headings are then classified into levels (H1, H2, H3, etc.) by sorting their unique font sizes in descending order.

### Round 1B: Persona-Driven Intelligence

Round 1B adds a layer of semantic understanding to rank document sections based on their relevance to a user's query.

1.  **Section Grouping**: A "section" is defined as a heading plus all the text content that follows it, up to the next heading. A function groups the raw text blocks from the PDF into these structured sections.

2.  **Semantic Embeddings**: The `Sentence-Transformers` library is used with the `all-MiniLM-L6-v2` model. This lightweight (~86MB) but powerful model converts both the user's query and the text content of each section into numerical vectors (embeddings).

3.  **Cosine Similarity**: To measure relevance, the cosine similarity between the user's query vector and each section's vector is calculated. A higher score (closer to 1.0) indicates a stronger semantic match.

4.  **Ranking**: The sections are then sorted in descending order based on their cosine similarity score to produce the final importance ranking.

## Libraries and Models

*   **Programming Language**: Python 3.9
*   **PDF Parsing**: `PyMuPDF` (fitz)
*   **NLP / Semantic Model**: `Sentence-Transformers` with the `all-MiniLM-L6-v2` model.
*   **Core Libraries**: `torch` (for Sentence-Transformers)

## How to Build and Run

### Prerequisites

*   Docker Desktop installed and running.
*   A sample PDF file placed in the `input/` directory.

### 1. Build the Docker Image

Navigate to the project's root directory in your terminal and run the following command:

```bash
docker build --platform linux/amd64 -t adobe-solution:latest .
```

### 2. Run the Solution

#### For Round 1A (Outline Extraction)

To generate the JSON outline, run the container with the input and output directories mounted:

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none adobe-solution:latest
```

This will process all PDFs in `input/` and create `*_outline.json` files in the `output/` directory.

#### For Round 1B (Persona-Driven Ranking)

To run the semantic ranking, you need to pass the persona and job-to-be-done as environment variables (`ADOBE_PERSONA` and `ADOBE_JOB`). The script will process all PDFs in the `input/` directory as a single collection.

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output -e ADOBE_PERSONA="Your Persona Here" -e ADOBE_JOB="Your Job-to-be-Done Here" --network none adobe-solution:latest
```

Replace the placeholder text with the actual persona and job. This will create a single `round_1b_analysis.json` file in the `output/` directory.