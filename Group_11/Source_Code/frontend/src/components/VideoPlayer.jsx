import { useEffect, useRef, useState } from "react";
const WEBSOCKET_URL = "ws://localhost:8000/ws/video";

export default function VideoPlayer() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);

  const [videoUrl, setVideoUrl] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [receivedFrame, setReceivedFrame] = useState(null);

  function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    setVideoUrl(url);
  }

  /* ---------- WebSocket setup ---------- */
  useEffect(() => {
    wsRef.current = new WebSocket(WEBSOCKET_URL);
    wsRef.current.binaryType = "arraybuffer";

    wsRef.current.onopen = () => console.log("WebSocket connected");

    wsRef.current.onmessage = (event) => {
      const bytes = new Uint8Array(event.data);
      const blob = new Blob([bytes], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);

      setReceivedFrame((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return url;
      });
    };

    wsRef.current.onclose = () => console.log("WebSocket disconnected");

    return () => wsRef.current?.close();
  }, []);

  /* ---------- Send one frame ---------- */
  const sendFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ws = wsRef.current;

    if (!video || !canvas || ws?.readyState !== WebSocket.OPEN) return;
    if (video.paused || video.ended) return;

    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) ws.send(blob);
      },
      "image/jpeg",
      0.5,
    );
  };

  /* ---------- Start / Stop streaming ---------- */
  useEffect(() => {
    if (isStreaming) {
      intervalRef.current = setInterval(sendFrame, 1000 / 10); // 10 FPS
      console.log("Streaming started");
    } else {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      console.log("Streaming stopped");
    }

    return () => clearInterval(intervalRef.current);
  }, [isStreaming]);

  /* ---------- Play / Pause ---------- */
  const handlePlay = () => {
    videoRef.current.play();
    setIsStreaming(true);
  };

  const handlePause = () => {
    videoRef.current.pause();
    setIsStreaming(false);
  };

  return (
    <div className="video-container box" style={{ flex: 3 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>CCTV Footage</h2>
        <input
          type="file"
          accept="video/*"
          onChange={handleUpload}
          placeholder="Upload"
        />
      </div>
      {/* Hidden Video Player */}
      <>
        <video
          ref={videoRef}
          src={videoUrl}
          controls={false}
          style={{ display: "none" }}
        />

        <canvas ref={canvasRef} style={{ display: "none" }} />
      </>
      {/* Placeholder or Processed Frame */}
      {receivedFrame ? (
        <div>
          {/* <h3 className="">Processed Frame (from backend)</h3> */}
          <img
            src={receivedFrame}
            alt="Received frame"
            className="received-frame video-placeholder"
          />
        </div>
      ) : (
        <div className="video-placeholder">
          <p>Live Stream Feed</p>
        </div>
      )}
      {/* Play/Pause Sending Frames */}
      <div style={{ marginTop: "8px", marginLeft: " 40%" }}>
        <button
          onClick={handlePlay}
          className="playback-btn"
          style={{ backgroundColor: "green" }}
        >
          ▶Play
        </button>

        <button
          onClick={handlePause}
          className="playback-btn"
          style={{ backgroundColor: "red" }}
        >
          ⏸Pause
        </button>
      </div>
    </div>
  );
}
