from sentence_transformers import SentenceTransformer

def download_model():
    """Downloads and saves the specified Sentence-Transformers model."""
    # This model is small (~86MB) and powerful.
    model_name = 'all-MiniLM-L6-v2'
    print(f"Downloading model: {model_name}...")
    
    model = SentenceTransformer(model_name)
    save_path = 'models/all-MiniLM-L6-v2'
    model.save(save_path)
    
    print(f"Model '{model_name}' downloaded and saved to '{save_path}'")

if __name__ == "__main__":
    download_model()