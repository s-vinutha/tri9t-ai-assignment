import difflib
from sqlalchemy.orm import Session
import app.models as models
from app.pdf_parser import parse_pdf_manual

def ingest_and_align_version(db: Session, pdf_path: str, target_version: int) -> dict:
    """
    Ingests a raw PDF manual version, maps layout components across existing iterations, 
    and handles semantic alignment checks or code mutation detection.
    """
    # 1. Parse layout items into a standard dictionary sequence using the parser engine
    extracted_nodes = parse_pdf_manual(pdf_path, version=target_version)
    
    report = {
        "version": target_version,
        "nodes_processed": len(extracted_nodes),
        "stable_nodes": 0,
        "mutations_detected": 0,
        "new_additions": 0
    }
    
    for incoming_node in extracted_nodes:
        # Match alignment targeting the previous active operational version
        historical_match = db.query(models.DocumentNode).filter(
            models.DocumentNode.version == target_version - 1,
            models.DocumentNode.heading == incoming_node['heading']
        ).first()
        
        if historical_match:
            # Reassign and bind the parent logical tracker token value
            incoming_node['id'] = historical_match.id
            
            # Evaluate content hash deviations
            if historical_match.content_hash == incoming_node['content_hash']:
                report["stable_nodes"] += 1
            else:
                report["mutations_detected"] += 1
        else:
            # Completely fresh layout branch encountered
            report["new_additions"] += 1
            
        # Write clean record updates directly into SQLite transactional scopes
        db_node = models.DocumentNode(
            id=incoming_node['id'],
            version=incoming_node['version'],
            heading=incoming_node['heading'],
            level=incoming_node['level'],
            body_text=incoming_node['body_text'],
            content_hash=incoming_node['content_hash'],
            parent_id=incoming_node['parent_id']
        )
        db.add(db_node)
        
    db.commit()
    return report

def compute_text_diff(text_v1: str, text_v2: str) -> str:
    """Generates a clean character-line delta comparison string report."""
    if not text_v1: text_v1 = ""
    if not text_v2: text_v2 = ""
    
    diff = difflib.ndiff(text_v1.splitlines(), text_v2.splitlines())
    return "\n".join([line for line in diff if line.startswith(('+', '-', '?'))])