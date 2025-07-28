import os
import json
import glob
from .round_1a import generate_outline_from_pdf
from .round_1b import generate_ranked_sections_from_pdf

def main():
    """
    Main function to drive the PDF processing workflow.
    It checks for environment variables to decide whether to run
    the simple outline extraction (Round 1A) or the persona-driven
    semantic search (Round 1B).
    """
    persona = os.environ.get("ADOBE_PERSONA")
    job = os.environ.get("ADOBE_JOB")
    input_dir = "input"
    output_dir = "output"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- Workflow Selection ---
    if persona and job:
        # --- Round 1B: Persona-Driven Semantic Search ---
        print("Starting Round 1B: Persona-Driven Document Intelligence...")

        # Scan all subdirectories of 'input' for PDFs, excluding '1a'
        pdf_paths = []
        for folder in os.listdir(input_dir):
            folder_path = os.path.join(input_dir, folder)
            if os.path.isdir(folder_path) and folder != '1a':
                pdf_paths.extend(glob.glob(os.path.join(folder_path, "*.pdf")))

        if not pdf_paths:
            print("No PDFs found for Round 1B processing.")
            return

        print(f"Found {len(pdf_paths)} PDF(s) to process for Round 1B.")
        
        # Generate ranked sections
        ranked_output = generate_ranked_sections_from_pdf(pdf_paths, persona, job)

        # Save the output
        output_path = os.path.join(output_dir, "round_1b_analysis.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ranked_output, f, indent=4)
        
        print(f"Round 1B analysis complete. Output saved to {output_path}")

    else:
        # --- Round 1A: Simple Outline Extraction ---
        print("Starting Round 1A: PDF Outline Extraction...")
        
        # Process PDFs only in the 'input/1a' directory
        round_1a_input_dir = os.path.join(input_dir, "1a")
        if not os.path.exists(round_1a_input_dir):
            print(f"Directory not found: {round_1a_input_dir}")
            return

        pdf_paths = glob.glob(os.path.join(round_1a_input_dir, "*.pdf"))

        if not pdf_paths:
            print(f"No PDFs found in {round_1a_input_dir}.")
            return

        for pdf_path in pdf_paths:
            print(f"Processing {os.path.basename(pdf_path)} for Round 1A...")
            try:
                outline_json = generate_outline_from_pdf(pdf_path)
                
                output_filename = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_outline.json"
                output_path = os.path.join(output_dir, output_filename)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(outline_json)
                print(f"Outline saved to {output_path}")

            except Exception as e:
                print(f"Error processing {os.path.basename(pdf_path)}: {e}")

        print("Round 1A processing complete.")


if __name__ == "__main__":
    main()
