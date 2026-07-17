from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Node Schema Layouts ---
class NodeResponse(BaseModel):
    id: str
    version: int
    heading: str
    level: int
    body_text: Optional[str] = None
    content_hash: str
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True

class NodeDiffResponse(BaseModel):
    id: str
    heading: str
    has_changed: bool
    version_1_hash: str
    version_2_hash: str
    diff_summary: str

# --- Selection Payload Layouts ---
class SelectionCreate(BaseModel):
    id: str
    name: str
    node_ids: List[str]
    version: int

class SelectionResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    version_pinned: int
    nodes_included: List[str]

    class Config:
        from_attributes = True

# --- LLM Structured Output & Resilience Layouts ---
class TestCaseItem(BaseModel):
    id: str = Field(description="Unique short code identifier, e.g., TC_BP_001")
    scenario: str = Field(description="Concrete QA scenario being validated")
    preconditions: List[str] = Field(description="System state prerequisites before execution[cite: 3]")
    steps: List[str] = Field(description="Step-by-step actions required by the tester[cite: 3]")
    expected_result: str = Field(description="Explicit expected system response[cite: 3]")

class GeneratedTestCasesResponse(BaseModel):
    selection_id: str
    target_nodes: List[str]
    test_cases: List[TestCaseItem]
    generated_at: str