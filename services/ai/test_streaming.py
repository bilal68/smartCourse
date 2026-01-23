#!/usr/bin/env python3
"""Quick test script for RAG streaming endpoint."""

import requests
import json
import sys

def test_streaming():
    url = "http://127.0.0.1:8001/api/v1/rag/ask/stream"
    
    payload = {
        "question": "What are advanced concepts?",  # Change this question!
        "mode": "student",
        "provider": "groq"
    }
    
    print("🔥 Testing RAG Streaming...")
    print(f"Question: {payload['question']}")
    print("=" * 50)
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return
            
        print("⚡ Streaming response:")
        print("-" * 30)
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = decoded_line[6:]  # Remove 'data: ' prefix
                    
                    if data.strip() == '':
                        continue
                        
                    try:
                        # Try to parse as JSON (metadata)
                        parsed = json.loads(data)
                        if isinstance(parsed, dict) and parsed.get('type') == 'start':
                            print(f"\n📍 Question: {parsed['question']}")
                            print(f"🤖 Provider: {parsed['model_info']['provider']} ({parsed['model_info']['model']})")
                            print(f"📊 Sources: {len(parsed['sources'])} chunks found")
                            print(f"🔥 Streaming: ", end='', flush=True)
                        elif isinstance(parsed, dict) and parsed.get('type') == 'error':
                            print(f"\n❌ Error: {parsed['error']}")
                        elif isinstance(parsed, str):
                            # This is streaming text
                            print(parsed, end='', flush=True)
                    except json.JSONDecodeError:
                        # Raw text without JSON quotes
                        print(data, end='', flush=True)
        
        print(f"\n\n✅ Stream completed!")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure your AI service is running on port 8001")
    except KeyboardInterrupt:
        print(f"\n⏹️ Stream interrupted by user")

if __name__ == "__main__":
    test_streaming()