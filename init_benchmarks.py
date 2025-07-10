#!/usr/bin/env python3
"""Initialize benchmark data for testing the tamper-proof system"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from apps.backend.database import get_engine, get_session
from apps.backend.models import Benchmark, SQLModel
from sqlmodel import Session

def init_benchmarks():
    """Add initial TruthfulQA and GSM8K benchmarks with dataset SHAs"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Check if benchmarks already exist
        existing = session.exec(session.query(Benchmark)).first()
        if existing:
            print("Benchmarks already initialized")
            return
        
        benchmarks = [
            Benchmark(
                name="TruthfulQA",
                version="5-shot",
                dataset_sha="a1b2c3d4e5f6"  # Mock SHA for demo
            ),
            Benchmark(
                name="GSM8K",
                version="5-shot", 
                dataset_sha="f6e5d4c3b2a1"  # Mock SHA for demo
            )
        ]
        
        for benchmark in benchmarks:
            session.add(benchmark)
        
        session.commit()
        print(f"Initialized {len(benchmarks)} benchmarks:")
        for b in benchmarks:
            print(f"  - {b.name} (v{b.version}) SHA: {b.dataset_sha}")

if __name__ == "__main__":
    init_benchmarks()