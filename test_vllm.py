#!/usr/bin/env python3
"""
Simple test script to verify VLLM service is working
"""

import requests
import json
import time
import sys


def test_vllm_health():
    """Test if VLLM service is running and healthy"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ VLLM service is healthy")
            return True
        else:
            print(f"❌ VLLM health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to VLLM service: {e}")
        return False


def test_vllm_completion():
    """Test VLLM completion endpoint"""
    try:
        payload = {
            "model": "tinyllama",
            "messages": [
                {"role": "user", "content": "Hello! Please respond with just 'Hi there!'"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0]["message"]["content"]
                print(f"✅ VLLM completion test successful: {message.strip()}")
                return True
            else:
                print("❌ VLLM completion test failed: no choices in response")
                return False
        else:
            print(f"❌ VLLM completion test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ VLLM completion test failed: {e}")
        return False


def main():
    print("🧪 Testing VLLM service...")
    print("=" * 50)
    
    # Wait a bit for service to start
    print("⏳ Waiting for VLLM service to start...")
    time.sleep(5)
    
    # Test health endpoint
    if not test_vllm_health():
        print("\n❌ VLLM service is not running or not healthy")
        print("💡 Try running: docker compose up vllm")
        sys.exit(1)
    
    # Test completion endpoint
    if not test_vllm_completion():
        print("\n❌ VLLM completion test failed")
        sys.exit(1)
    
    print("\n🎉 All tests passed! VLLM service is working correctly.")


if __name__ == "__main__":
    main()