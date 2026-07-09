import asyncio
import httpx
import websockets
import json
import sys

async def test_rest_api():
    print("Testing REST API on port 8000...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/settings", timeout=5.0)
            print(f"REST API Response Status: {response.status_code}")
            if response.status_code == 200:
                print("REST API settings fetch successful!")
                print(f"Data: {response.json()}")
                return True
            else:
                print(f"REST API failed with unexpected status: {response.status_code}")
                return False
        except Exception as e:
            print(f"REST API connection failed: {e}")
            return False

async def test_websocket():
    print("\nTesting WebSocket connection on ws://localhost:8000/ws...")
    uri = "ws://localhost:8000/ws?session_id=test-session-123&caller_phone=%2B1234567890"
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connection established successfully!")
            
            # Send heartbeat ping message
            print("Sending 'ping' to server...")
            await websocket.send("ping")
            
            # Receive response
            print("Waiting for response from server...")
            response = await websocket.recv()
            print(f"Received from server: {response}")
            
            if response == "pong":
                print("WebSocket ping/pong check passed!")
                return True
            else:
                print(f"Unexpected response from server: {response}")
                return False
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        return False

async def main():
    print("========================================")
    print("AIRA Unified Port Verification Script")
    print("========================================\n")
    
    api_ok = await test_rest_api()
    ws_ok = await test_websocket()
    
    print("\n========================================")
    if api_ok and ws_ok:
        print("SUCCESS: Both REST API and WebSocket are working on port 8000!")
        sys.exit(0)
    else:
        print("FAILURE: Verification failed. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
