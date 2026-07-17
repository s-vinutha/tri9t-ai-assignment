import os
import json
import datetime
from typing import List
from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

import app.models as models
import app.schemas as schemas

# Initialize the LLM client engine wrapper targeting a free-tier provider
# Ensure your GROQ_API_KEY environment variable is configured inside your local .env file!
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY", "MOCK_KEY_IF_TESTING")
)

# Mock JSON file-based NoSQL datastore to satisfy the assignment scope easily without configuring full MongoDB
NOSQL_JSON_STORE_PATH = "./local_nosql_testcases.json"

def save_to_nosql_datastore(selection_id: str, data_payload: dict):
    """Persists validated JSON outputs cleanly into a decoupled JSON structural store."""
    store = {}
    if os.path.exists(NOSQL_JSON_STORE_PATH):
        try:
            with open(NOSQL_JSON_STORE_PATH, "r") as f:
                store = json.load(f)
        except Exception:
            store = {}
            
    # Assign payload mapped explicitly to the unique selection signature block
    store[selection_id] = data_payload
    
    with open(NOSQL_JSON_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)

def fetch_from_nosql_datastore(selection_id: str) -> dict:
    """Retrieves raw JSON test case maps from the local file matrix store."""
    if os.path.exists(NOSQL_JSON_STORE_PATH):
        try:
            with open(NOSQL_JSON_STORE_PATH, "r") as f:
                store = json.load(f)
                return store.get(selection_id, {})
        except Exception:
            return {}
    return {}

def generate_validated_test_cases(
    db: Session, 
    selection_id: str, 
    reconstructed_text: str, 
    target_node_ids: List[str]
) -> dict:
    """
    Orchestrates systemic LLM prompts, forces response streams through strict Pydantic 
    verification schemas, and manages a dual-pass correction repair loop if JSON drops fields.
    """
    
    # 1. Defend policy choice for duplicate submissions: Return historical record to prevent resource drain[cite: 3]
    existing_records = fetch_from_nosql_datastore(selection_id)
    if existing_records:
        print(f"ℹ️ Selection ID {selection_id} matches existing cache. Returning historical dataset[cite: 3].")
        return existing_records

    system_prompt = (
        "You are an expert Medical Device QA Engineer specializing in IEC 62304 and ISO 14971 validation[cite: 3].\n"
        "Your task is to review the provided technical document text and generate exactly 3 to 5 highly concrete, "
        "repeatable, and explicit QA test-case ideas[cite: 3].\n\n"
        "CRITICAL FORMAT RULES:\n"
        "1. You must respond with raw JSON that matches the exact keys requested: 'selection_id', 'target_nodes', and 'test_cases'[cite: 3].\n"
        "2. The 'test_cases' field must be an array of objects, containing 'id', 'scenario', 'preconditions', 'steps', and 'expected_result'[cite: 3].\n"
        "3. Do NOT wrap your output string inside markdown blocks like ```json. Return raw text only[cite: 3].\n"
        "4. Include absolutely no pleasantries, summary notes, or conversational text[cite: 3]."
    )

    user_prompt = f"Target Documentation Framework:\n{reconstructed_text}"
    
    max_retries = 2
    attempt = 0
    feedback_context = ""

    while attempt <= max_retries:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            if feedback_context:
                messages.append({"role": "assistant", "content": feedback_context})
                messages.append({"role": "user", "content": "Your previous response generated a verification error. Fix your output structure."})

            # Execute completion loop against free-tier LLM system architecture[cite: 3]
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.0  # Zero temperature forces absolute deterministic structural outputs
            )
            
            raw_text_payload = response.choices[0].message.content.strip()
            
            # 2. Attempt native JSON conversion parsing block
            parsed_data = json.loads(raw_text_payload)
            
            # 3. Enforce schema integrity validation against explicit Pydantic blueprints[cite: 3]
            validated_response = schemas.GeneratedTestCasesResponse(
                selection_id=selection_id,
                target_nodes=target_node_ids,
                test_cases=parsed_data.get("test_cases", []),
                generated_at=str(datetime.datetime.utcnow())
            )
            
            # Success! Extract payload dictionary and write to data backup engine mapping[cite: 3]
            final_dictionary = validated_response.model_dump()
            save_to_nosql_datastore(selection_id, final_dictionary)
            return final_dictionary

        except (json.JSONDecodeError, ValidationError) as parsing_error:
            attempt += 1
            print(f"⚠️ Pydantic/JSON Schema validation breakdown on attempt {attempt}: {str(parsing_error)}[cite: 3]")
            # Log raw trace error signatures to build the self-correction contextual prompt array[cite: 3]
            feedback_context = f"Failed Data Output: {raw_text_payload}\nError Parameters: {str(parsing_error)}"
            
    # Structural generation engine failure after complete loop pass: Raise explicit exception[cite: 3]
    raise ValueError("LLM execution processing failed to output clean valid schema parameters after total retries[cite: 3].")