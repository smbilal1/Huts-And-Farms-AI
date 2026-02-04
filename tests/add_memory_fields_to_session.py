"""
Database Migration: Add Memory Fields to Session Table

This script adds the required fields for the LangGraph memory system:
- conversation_summary: Text field for compressed conversation summary
- summary_updated_at: Timestamp of last summary update
- summary_generation_count: Counter for adaptive compression
- needs_summarization: Flag set by tools when state changes
"""

from sqlalchemy import text
from app.database import engine


def add_memory_fields():
    """Add memory management fields to sessions table."""
    
    print("🔧 Adding memory fields to sessions table...")
    
    try:
        with engine.begin() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sessions' 
                AND column_name IN ('conversation_summary', 'summary_updated_at', 'summary_generation_count', 'needs_summarization');
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add conversation_summary if not exists
            if 'conversation_summary' not in existing_columns:
                print("  → Adding conversation_summary column...")
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN conversation_summary TEXT;
                """))
                print("    ✅ conversation_summary added")
            else:
                print("    ℹ️  conversation_summary already exists")
            
            # Add summary_updated_at if not exists
            if 'summary_updated_at' not in existing_columns:
                print("  → Adding summary_updated_at column...")
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN summary_updated_at TIMESTAMP;
                """))
                print("    ✅ summary_updated_at added")
            else:
                print("    ℹ️  summary_updated_at already exists")
            
            # Add summary_generation_count if not exists
            if 'summary_generation_count' not in existing_columns:
                print("  → Adding summary_generation_count column...")
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN summary_generation_count INTEGER DEFAULT 0;
                """))
                print("    ✅ summary_generation_count added")
            else:
                print("    ℹ️  summary_generation_count already exists")
            
            # Add needs_summarization if not exists
            if 'needs_summarization' not in existing_columns:
                print("  → Adding needs_summarization column...")
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN needs_summarization BOOLEAN DEFAULT FALSE;
                """))
                print("    ✅ needs_summarization added")
            else:
                print("    ℹ️  needs_summarization already exists")
        
        print("\n✅ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("  1. Update state-changing tools to call mark_state_change()")
        print("  2. Test the memory system with a conversation")
        print("  3. Monitor summary generation in logs")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    add_memory_fields()
