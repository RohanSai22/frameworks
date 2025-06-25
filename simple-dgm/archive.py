import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class SimpleArchive:
    def __init__(self, db_path="archive/agents.db"):
        """Initialize the archive to store agent versions and their performance"""
        self.db_path = db_path
        
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.init_database()
        
    def init_database(self):
        """Create the database tables for storing agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parent_id INTEGER,
                description TEXT,
                metadata TEXT,
                is_functional BOOLEAN DEFAULT 1
            )
        """)
        
        # Performance history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                test_name TEXT,
                score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents (id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_score ON agents(score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_created ON agents(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_parent ON agents(parent_id)")
        
        conn.commit()
        conn.close()
        
    def save_agent(self, code: str, score: float, parent_id: Optional[int] = None, 
                   description: str = "", metadata: Dict = None, is_functional: bool = True) -> int:
        """Save a new agent version to the archive"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT INTO agents (code, score, parent_id, description, metadata, is_functional)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, score, parent_id, description, metadata_json, is_functional))
        
        agent_id = cursor.lastrowid
        
        # Also save to performance history
        cursor.execute("""
            INSERT INTO performance_history (agent_id, test_name, score)
            VALUES (?, ?, ?)
        """, (agent_id, "main_benchmark", score))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Saved agent {agent_id} with score {score:.3f}")
        return agent_id
        
    def get_agent(self, agent_id: int) -> Optional[Dict]:
        """Get a specific agent by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, code, score, created_at, parent_id, description, metadata, is_functional
            FROM agents WHERE id = ?
        """, (agent_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'code': result[1], 
                'score': result[2],
                'created_at': result[3],
                'parent_id': result[4],
                'description': result[5],
                'metadata': json.loads(result[6] or '{}'),
                'is_functional': bool(result[7])
            }
        return None
        
    def get_best_agent(self) -> Optional[Dict]:
        """Get the agent with the highest score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, code, score, created_at, parent_id, description, metadata, is_functional
            FROM agents 
            WHERE is_functional = 1
            ORDER BY score DESC, created_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'code': result[1],
                'score': result[2], 
                'created_at': result[3],
                'parent_id': result[4],
                'description': result[5],
                'metadata': json.loads(result[6] or '{}'),
                'is_functional': bool(result[7])
            }
        return None
        
    def get_all_agents(self, functional_only: bool = True) -> List[Dict]:
        """Get all agents, optionally filtered by functionality"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if functional_only:
            cursor.execute("""
                SELECT id, code, score, created_at, parent_id, description, metadata, is_functional
                FROM agents 
                WHERE is_functional = 1
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, code, score, created_at, parent_id, description, metadata, is_functional  
                FROM agents
                ORDER BY created_at DESC
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        agents = []
        for result in results:
            agents.append({
                'id': result[0],
                'code': result[1],
                'score': result[2],
                'created_at': result[3], 
                'parent_id': result[4],
                'description': result[5],
                'metadata': json.loads(result[6] or '{}'),
                'is_functional': bool(result[7])
            })
        
        return agents
        
    def get_top_agents(self, n: int = 5) -> List[Dict]:
        """Get the top N performing agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, code, score, created_at, parent_id, description, metadata, is_functional
            FROM agents 
            WHERE is_functional = 1
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (n,))
        
        results = cursor.fetchall()
        conn.close()
        
        agents = []
        for result in results:
            agents.append({
                'id': result[0],
                'code': result[1],
                'score': result[2],
                'created_at': result[3],
                'parent_id': result[4], 
                'description': result[5],
                'metadata': json.loads(result[6] or '{}'),
                'is_functional': bool(result[7])
            })
        
        return agents
        
    def get_lineage(self, agent_id: int) -> List[Dict]:
        """Get the lineage (ancestry) of an agent"""
        lineage = []
        current_id = agent_id
        
        while current_id is not None:
            agent = self.get_agent(current_id)
            if agent:
                lineage.append(agent)
                current_id = agent['parent_id']
            else:
                break
                
        return lineage
        
    def get_statistics(self) -> Dict:
        """Get archive statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total agents
        cursor.execute("SELECT COUNT(*) FROM agents")
        total_agents = cursor.fetchone()[0]
        
        # Functional agents
        cursor.execute("SELECT COUNT(*) FROM agents WHERE is_functional = 1")
        functional_agents = cursor.fetchone()[0]
        
        # Best score
        cursor.execute("SELECT MAX(score) FROM agents WHERE is_functional = 1")
        best_score = cursor.fetchone()[0] or 0.0
        
        # Average score
        cursor.execute("SELECT AVG(score) FROM agents WHERE is_functional = 1")
        avg_score = cursor.fetchone()[0] or 0.0
        
        # Score improvement over time
        cursor.execute("""
            SELECT created_at, score FROM agents 
            WHERE is_functional = 1 
            ORDER BY created_at ASC
        """)
        score_history = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_agents': total_agents,
            'functional_agents': functional_agents,
            'success_rate': functional_agents / total_agents if total_agents > 0 else 0,
            'best_score': best_score,
            'average_score': avg_score,
            'score_history': score_history
        }
        
    def select_parents(self, k: int = 2, selection_strategy: str = "weighted") -> List[Dict]:
        """
        Select parent agents for the next generation
        Based on DGM paper's selection strategy
        """
        functional_agents = self.get_all_agents(functional_only=True)
        
        if not functional_agents:
            return []
            
        if len(functional_agents) < k:
            return functional_agents
        else:
            sorted_agents = sorted(functional_agents, key=lambda x: x["score"], reverse=True)
            return sorted_agents[:k]
        
    def export_best_agent(self, output_path: str):
        """Export the best agent to a file"""
        best_agent = self.get_best_agent()
        
        if best_agent:
            with open(output_path, 'w') as f:
                f.write(f"# Best Agent (ID: {best_agent['id']}, Score: {best_agent['score']:.3f})\n")
                f.write(f"# Created: {best_agent['created_at']}\n") 
                f.write(f"# Description: {best_agent['description']}\n\n")
                f.write(best_agent['code'])
            print(f"✓ Exported best agent to {output_path}")
        else:
            print("✗ No agents found to export")
            
    def cleanup_old_agents(self, keep_n: int = 100):
        """Keep only the best N agents to manage database size"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Keep top N functional agents and all non-functional ones
        cursor.execute("""
            DELETE FROM agents 
            WHERE id NOT IN (
                SELECT id FROM agents 
                WHERE is_functional = 1 
                ORDER BY score DESC 
                LIMIT ?
            ) AND is_functional = 1
        """, (keep_n,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✓ Cleaned up {deleted_count} old agents")

if __name__ == "__main__":
    # Test the archive system
    archive = SimpleArchive()
    
    # Add some test agents
    agent1_id = archive.save_agent("# Agent 1 code", 0.25, description="Initial agent")
    agent2_id = archive.save_agent("# Agent 2 code", 0.35, parent_id=agent1_id, description="Improved agent")
    agent3_id = archive.save_agent("# Agent 3 code", 0.45, parent_id=agent2_id, description="Better agent")
    
    # Test retrieval
    best = archive.get_best_agent()
    print(f"Best agent: ID {best['id']} with score {best['score']}")
    
    # Test statistics
    stats = archive.get_statistics()
    print(f"Archive stats: {stats}")
    
    # Test parent selection
    parents = archive.select_parents(k=2)
    print(f"Selected parents: {[p['id'] for p in parents]}") 