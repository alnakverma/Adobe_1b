import json
import os
import datetime
import fitz
import re
from sentence_transformers import SentenceTransformer, util
import torch
from . import round_1a
from .round_1a import (
    extract_text_blocks,
    get_body_text_style,
    identify_and_classify_headings,
    group_text_into_sections,
)

# --- HELPER FUNCTIONS ---
MODEL_PATH = 'models/all-MiniLM-L6-v2'
STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "o", "of", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should",
    "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with", "you", "your",
    "yours", "yourself", "yourselves", "i'd", "i'll", "i'm", "i've", "need", "find", "information", "on",
    "key", "to", "and", "a", "the", "of"
])

def load_model():
    print(f"Loading model from {MODEL_PATH}...")
    device = 'cpu'
    model = SentenceTransformer(MODEL_PATH, device=device)
    print(f"Model loaded successfully on {device}.")
    return model

def rank_sections_by_relevance(model, query, items):
    if not items: return []
    contents = [item['content'] for item in items]
    try:
        embeddings = model.encode(contents, convert_to_tensor=True, show_progress_bar=False)
        query_embedding = model.encode(query, convert_to_tensor=True)
    except Exception as e:
        print(f"Error during model encoding: {e}")
        return []
    similarities = util.pytorch_cos_sim(query_embedding, embeddings)[0]
    for i, item in enumerate(items):
        item['semantic_score'] = similarities[i].item()
    return items

def chunk_text(text, chunk_size=250):
    sentences = text.split('\n')
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk.split()) + len(sentence.split()) <= chunk_size:
            current_chunk += sentence + "\n"
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            current_chunk = sentence + "\n"
    if current_chunk: chunks.append(current_chunk.strip())
    return chunks if chunks else [text.strip()]

def generate_keywords_from_query(text):
    normalized_text = re.sub(r'[^\w\s]', '', text.lower())
    words = normalized_text.split()
    keywords = [word for word in words if word not in STOP_WORDS and len(word) > 3]
    return list(set(keywords))

# --- MAIN ORCHESTRATOR FUNCTION ---
def generate_ranked_sections_from_pdf(pdf_paths, persona, job):
    model = load_model()
    query = f"Persona: {persona}. Job: {job}"

    # --- Pre-filtering using the text from the first 4 pages ---
    print("Pre-filtering documents using text from the first 4 pages...")
    docs_for_ranking = []
    for pdf_path in pdf_paths:
        try:
            doc = fitz.open(pdf_path)
            # Use the first 4 pages for a comprehensive summary
            initial_blocks = extract_text_blocks(doc, page_limit=4)
            doc.close()

            if not initial_blocks:
                print(f"  > No text found in first 4 pages of {os.path.basename(pdf_path)}")
                continue
            
            content_for_ranking = " ".join([b['text'] for b in initial_blocks])
            if content_for_ranking:
                docs_for_ranking.append({'path': pdf_path, 'content': content_for_ranking})
        except Exception as e:
            print(f"  > Error processing {os.path.basename(pdf_path)}: {e}")

    # --- Dynamic Keyword Generation ---
    KEYWORDS = generate_keywords_from_query(job)
    print(f"Generated dynamic keywords: {KEYWORDS}")

    # --- Hybrid Score Calculation ---
    docs_with_semantic_score = rank_sections_by_relevance(model, query, docs_for_ranking)
    for doc in docs_with_semantic_score:
        content_lower = doc['content'].lower()
        keyword_hits = sum(1 for keyword in KEYWORDS if keyword in content_lower)
        keyword_score = min(keyword_hits / 3.0, 1.0) # Normalize based on hitting ~3 keywords
        semantic_score = doc.get('semantic_score', 0)
        # Give keyword score a bit more weight to ensure it pulls up the right documents
        doc['final_score'] = (0.5 * semantic_score) + (0.5 * keyword_score)

    ranked_docs_final = sorted(docs_with_semantic_score, key=lambda x: x['final_score'], reverse=True)
    
    # --- Final Filtering with an Absolute Threshold ---
    FINAL_THRESHOLD = 0.20 # A solid confidence threshold

    print("\n--- Document Pre-filtering Scores ---")
    for doc in ranked_docs_final:
        print(f"  Score: {doc['final_score']:.2f} | File: {os.path.basename(doc['path'])}")
    print("-------------------------------------\n")
    print(f"Using a final absolute relevance threshold of {FINAL_THRESHOLD}.")

    relevant_docs = [doc for doc in ranked_docs_final if doc['final_score'] >= FINAL_THRESHOLD]
    top_pdf_paths = [doc['path'] for doc in relevant_docs[:5]]

    print(f"Identified top relevant documents: {[os.path.basename(p) for p in top_pdf_paths]}")
    
    if not top_pdf_paths:
        return {"metadata": {}, "extracted_section": [], "sub-section_analysis": []}

    # --- Process and Rank Sections from Top Documents ---
    all_sections = []
    for pdf_path in top_pdf_paths:
        doc_name = os.path.basename(pdf_path)
        print(f"Extracting sections from {doc_name}...")
        try:
            doc = fitz.open(pdf_path)
            blocks = extract_text_blocks(doc)
            doc.close()
            if not blocks: continue
            body_size, _ = get_body_text_style(blocks)
            headings, _ = identify_and_classify_headings(blocks, body_size)
            sections = group_text_into_sections(blocks, headings)
            for section in sections:
                section['document'] = doc_name
            all_sections.extend(sections)
        except Exception as e:
            print(f"Error processing sections for {pdf_path}: {e}")

    # Rank all sections using the same hybrid score logic
    sections_with_semantic_score = rank_sections_by_relevance(model, query, all_sections)
    for section in sections_with_semantic_score:
        keyword_hits = sum(1 for keyword in KEYWORDS if keyword in section['content'].lower())
        keyword_score = min(keyword_hits / 3.0, 1.0)
        section['final_score'] = (0.6 * section.get('semantic_score', 0)) + (0.4 * keyword_score)
    ranked_sections = sorted(sections_with_semantic_score, key=lambda x: x['final_score'], reverse=True)

    # --- Sub-section Analysis ---
    print("Performing sub-section analysis on top candidates...")
    top_k_sections = ranked_sections[:20]
    sub_section_candidates = []
    for section in top_k_sections:
        content_chunks = chunk_text(section['content'])
        for chunk in content_chunks:
            sub_section_candidates.append({'document': section['document'], 'page': section['page'], 'content': chunk})
    
    sub_sections_with_semantic_score = rank_sections_by_relevance(model, query, sub_section_candidates)
    for sub_section in sub_sections_with_semantic_score:
        keyword_hits = sum(1 for keyword in KEYWORDS if keyword in sub_section['content'].lower())
        keyword_score = min(keyword_hits / 3.0, 1.0)
        sub_section['final_score'] = (0.6 * sub_section.get('semantic_score', 0)) + (0.4 * keyword_score)
    ranked_sub_sections = sorted(sub_sections_with_semantic_score, key=lambda x: x['final_score'], reverse=True)

    # --- Format Final JSON Output ---
    output_json = {
        "metadata": {"input_documents": [os.path.basename(p) for p in pdf_paths], "persona": persona, "job_to_be_done": job, "processing_timestamp": datetime.datetime.now().isoformat()},
        "extracted_section": [{"document": s['document'], "page_number": s['page'], "section_title": s.get('heading_text', 'Untitled'), "importance_rank": i + 1} for i, s in enumerate(ranked_sections)],
        "sub-section_analysis": [{"document": s['document'], "refined_text": s['content'], "page_number": s['page']} for s in ranked_sub_sections[:10]]
    }
    return output_json