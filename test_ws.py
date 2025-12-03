import asyncio
import websockets
import json


async def test_connection():
    uri = "ws://localhost:8021/ws/test-room"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")

            # Send a sync step 1 message (y-websocket protocol)
            # This is just to keep the connection alive and see if it closes
            # 0: sync, 0: step 1, ...
            # We can just wait and see if it closes

            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"Received: {msg}")
            except asyncio.TimeoutError:
                print("No message received in 10s (expected if no other client)")

            print("Keeping connection open for 5s...")
            await asyncio.sleep(5)
            print("Closing connection...")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())
