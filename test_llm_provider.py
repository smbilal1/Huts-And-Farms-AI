"""
Test script to verify LLM provider configuration.

Usage:
    python test_llm_provider.py
"""

from app.core.config import settings
from app.agents.llm_factory import get_llm, get_embedding_function

def test_llm_provider():
    """Test the configured LLM provider."""
    
    print("=" * 60)
    print("🧪 Testing LLM Provider Configuration")
    print("=" * 60)
    
    # Show current configuration
    print(f"\n📋 Current Configuration:")
    print(f"   LLM Provider: {settings.LLM_PROVIDER.upper()}")
    print(f"   OpenAI Key: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Not Set'}")
    print(f"   Google Key: {'✅ Set' if settings.GOOGLE_API_KEY else '❌ Not Set'}")
    
    # Test LLM initialization
    print(f"\n🤖 Testing LLM Initialization...")
    try:
        llm = get_llm(temperature=0)
        print(f"   ✅ LLM initialized successfully")
        print(f"   Model: {llm.__class__.__name__}")
    except Exception as e:
        print(f"   ❌ LLM initialization failed: {e}")
        return False
    
    # # Test embedding function
    # print(f"\n🔢 Testing Embedding Function...")
    # try:
    #     embed_fn = get_embedding_function()
    #     test_text = "Hello, this is a test."
    #     embedding = embed_fn(test_text)
    #     print(f"   ✅ Embedding generated successfully")
    #     print(f"   Dimensions: {len(embedding)}")
    #     print(f"   First 5 values: {embedding[:5]}")
    # except Exception as e:
    #     print(f"   ❌ Embedding generation failed: {e}")
    #     return False
    
    # Test simple generation
    print(f"\n💬 Testing Text Generation...")
    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content="Say 'Hello World' and nothing else.")])
        print(f"   ✅ Generation successful")
        print(f"   Response: {response.content}")
    except Exception as e:
        print(f"   ❌ Generation failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_llm_provider()
    exit(0 if success else 1)
