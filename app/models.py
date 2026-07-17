import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Table, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from app.database import Base

# Many-to-Many association junction linking selections explicitly to version-pinned nodes
selection_node_association = Table(
    'selection_node_association',
    Base.metadata,
    Column('selection_id', String, ForeignKey('selections.id'), primary_key=True),
    Column('node_id', String, primary_key=True),
    Column('version', Integer, primary_key=True),
    ForeignKeyConstraint(['node_id', 'version'], ['nodes.id', 'nodes.version'])
)

class DocumentNode(Base):
    __tablename__ = 'nodes'

    id = Column(String, primary_key=True)  # Shared logical slug identifier across matching updates
    version = Column(Integer, primary_key=True)  # Version iteration count index parameter
    
    heading = Column(String, nullable=False)
    level = Column(Integer, nullable=False)
    body_text = Column(Text, nullable=True)
    content_hash = Column(String, nullable=False)  # Checksum string used for automated change flags
    
    parent_id = Column(String, nullable=True)

class Selection(Base):
    __tablename__ = 'selections'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Snapshot reference pointing exactly to the specific nodes pinned at creation time
    nodes = relationship("DocumentNode", secondary=selection_node_association)