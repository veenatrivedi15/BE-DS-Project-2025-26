from fastapi import APIRouter, WebSocket, WebSocketDisconnect,Response
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import time
import base64
import asyncio

from frame_buffer import FrameBuffer
from output_buffer import ProcessedFrameBuffer
from vlm_buffer import VLMFrameBuffer

socket_router = APIRouter()

frame_buffer = FrameBuffer(max_seconds=20, target_fps=10)
processed_buffer = ProcessedFrameBuffer()
vlm_buffer = VLMFrameBuffer()


@socket_router.websocket("/video")
async def video_websocket(websocket: WebSocket):
    await websocket.accept()

    sending_enabled = asyncio.Event()
    connected = True
    print("[WS] Connected")

    async def receiver():
        try:
            nonlocal connected
            while connected:
                print("\nReceiving\n")
                frame_bytes = await websocket.receive_bytes()

                sending_enabled.set()

                frame = cv2.imdecode(
                    np.frombuffer(frame_bytes, np.uint8),
                    cv2.IMREAD_COLOR,
                )
                if frame is not None:
                    print("\nFrame added\n")
                    frame_buffer.add_frame(frame, time.time())
        except WebSocketDisconnect:
            print("\nRecieving Web Socket Disconnected\n")
            connected = False
            sending_enabled.set()
            pass

    async def sender():
        try:
            nonlocal connected
            while connected:
                await sending_enabled.wait()

                if not connected:
                    print("\n Sending looped breaking\n")
                    break

                print("\nSending...\n")
                
                item = processed_buffer.get_latest()
                if item:
                    timestamp, frame_bytes = item
                    if time.time() - timestamp < 1.5:
                        await websocket.send_bytes(frame_bytes)
                        print("\nFrame sent\n")
                    else:
                        sending_enabled.clear()

                await asyncio.sleep(0.1)  # ~10 FPS

        except WebSocketDisconnect:
            print("\nSending Web Socket Disconnected\n")
        finally:
            connected = False
            sending_enabled.clear()

    receive_task = asyncio.create_task(receiver())
    send_task = asyncio.create_task(sender())

    done, pending = await asyncio.wait(
        [receive_task, send_task],
        return_when=asyncio.FIRST_EXCEPTION
    )

    for task in pending:
        task.cancel()



@socket_router.get("/get_snaps")
async def get_snaps():
    frame = processed_buffer.get_latest()

    if frame is None:
        return Response(status_code=404)

    timestamp, frame_bytes = frame

    return Response(
        content=frame_bytes,
        media_type="image/jpeg"   # or image/png depending on your data
    )

@socket_router.get("/output_buffer")
async def get_output_buffer():
    """
    Return from the processed buffer
    as base64 strings.
    """
    # frames = processed_buffer.get_n_evenly_spaced(10)
    frames = vlm_buffer.get_full_buffer()
    encoded_frames = [base64.b64encode(f).decode("utf-8") for f in frames]
    return JSONResponse(content={"frames": encoded_frames})

