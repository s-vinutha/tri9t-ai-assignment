import uuid
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import app.models as models
import app.schemas as schemas
import app.version_engine as version_engine
from app.database import engine, get_db

# Initialize database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tri9T AI Compliance & Engineering Engine",
    description="Backend API for structural parsing, document versioning, and stale QA test case detection."
)

# --- 1. Browse & Search Endpoints ---

@app.get("/api/nodes", response_model=List[schemas.NodeResponse])
def list_document_nodes(
    version: int = Query(1, description="Target document manual version layer"),
    parent_id: Optional[str] = Query(None, description="Filter elements matching specific parent ID"),
    db: Session = Depends(get_db)
):
    """Fetches a browseable, structured sequence of nodes matching the document version layout[cite: 3]."""
    query = db.query(models.DocumentNode).filter(models.DocumentNode.version == version)
    if parent_id:
        query = query.filter(models.DocumentNode.parent_id == parent_id)
    return query.order_by(models.DocumentNode.heading).all()

@app.get("/api/nodes/search", response_model=List[schemas.NodeResponse])
def search_document_text(
    q: str = Query(..., description="Text string query to match inside headings or body lines[cite: 3]"),
    version: int = 1,
    db: Session = Depends(get_db)
):
    """Searches and filters target structural keywords or parameters across document text[cite: 3]."""
    results = db.query(models.DocumentNode).filter(
        models.DocumentNode.version == version,
        (models.DocumentNode.heading.ilike(f"%{q}%")) | (models.DocumentNode.body_text.ilike(f"%{q}%"))
    ).all()
    return results

@app.get("/api/nodes/{node_id}/diff", response_model=schemas.NodeDiffResponse)
def get_node_version_diff(node_id: str, db: Session = Depends(get_db)):
    """Computes a structural text line diff summary showing mutations between manual versions[cite: 3]."""
    node_v1 = db.query(models.DocumentNode).filter(models.DocumentNode.id == node_id, models.DocumentNode.version == 1).first()
    node_v2 = db.query(models.DocumentNode).filter(models.DocumentNode.id == node_id, models.DocumentNode.version == 2).first()
    
    if not node_v1 and not node_v2:
        raise HTTPException(status_code=404, detail="Node structure not located in storage system.")
        
    has_changed = False
    diff_report = "No modifications detected between versions."
    v1_hash = node_v1.content_hash if node_v1 else "DELETED/NON-EXISTENT"
    v2_hash = node_v2.content_hash if node_v2 else "DELETED/NON-EXISTENT"
    heading_title = node_v2.heading if node_v2 else node_v1.heading

    if node_v1 and node_v2:
        if node_v1.content_hash != node_v2.content_hash:
            has_changed = True
            diff_report = version_engine.compute_text_diff(node_v1.body_text, node_v2.body_text)
    elif node_v1 and not node_v2:
        has_changed = True
        diff_report = "Node deleted or structural pathway removed in Version 2[cite: 3]."
    elif not node_v1 and node_v2:
        has_changed = True
        diff_report = "Brand new structural node entry appended in Version 2[cite: 3]."

    return {
        "id": node_id,
        "heading": heading_title,
        "has_changed": has_changed,
        "version_1_hash": v1_hash,
        "version_2_hash": v2_hash,
        "diff_summary": diff_report
    }

# --- 2. Snapshot Selection Endpoints ---

@app.post("/api/selections", response_model=schemas.SelectionResponse)
def create_version_pinned_selection(payload: schemas.SelectionCreate, db: Session = Depends(get_db)):
    """Creates a named selection set pinned to explicit node version combinations[cite: 3]."""
    # Verify selection ID uniqueness
    existing_sel = db.query(models.Selection).filter(models.Selection.id == payload.id).first()
    if existing_sel:
        raise HTTPException(status_code=400, detail="Selection ID token conflict detected.")
        
    # Resolve and compile specific target node entities matching the version parameter
    target_nodes = db.query(models.DocumentNode).filter(
        models.DocumentNode.id.in_(payload.node_ids),
        models.DocumentNode.version == payload.version
    ).all()
    
    if len(target_nodes) != len(payload.node_ids):
        raise HTTPException(status_code=422, detail="One or more target Node IDs could not be resolved for this version.")
        
    new_selection = models.Selection(id=payload.id, name=payload.name)
    new_selection.nodes.extend(target_nodes)
    
    db.add(new_selection)
    db.commit()
    
    return {
        "id": new_selection.id,
        "name": new_selection.name,
        "created_at": new_selection.created_at,
        "version_pinned": payload.version,
        "nodes_included": [n.id for n in new_selection.nodes]
    }

# --- 3. Manual Processing Core Router Trigger ---

@app.post("/api/ingest-pipeline")
def run_manual_ingestion_pipeline(
    pdf_path: str = Query(..., description="Local server workspace string location path to raw PDF file"),
    version: int = Query(..., description="Target version code integer level mapping index"),
    db: Session = Depends(get_db)
):
    """Triggers the raw PDF visual layout extractor and aligns structural branches[cite: 3]."""
    try:
        processing_summary = version_engine.ingest_and_align_version(db, pdf_path, version)
        return {"status": "success", "pipeline_report": processing_summary}
    except Exception as error_logs:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failure: {str(error_logs)}")