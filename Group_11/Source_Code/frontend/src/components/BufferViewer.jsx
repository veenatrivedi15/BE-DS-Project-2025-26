import React, { useEffect, useState } from "react";

export default function BufferViewer() {
  const [images, setImages] = useState([]);

  // Fetch frames from FastAPI endpoint
  const fetchFrames = async () => {
    try {
      const response = await fetch("http://localhost:8000/ws/output_buffer");
      if (!response.ok) {
        console.error("Failed to fetch frames", response.status);
        return;
      }
      const data = await response.json();
      // Expecting data.frames = array of base64 strings
      setImages(data.frames || []);
    } catch (err) {
      console.error("Error fetching frames:", err);
    }
  };

  // Fetch on mount and optionally every N seconds
  useEffect(() => {
    fetchFrames();
    const interval = setInterval(fetchFrames, 5000); // refresh every 2 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h3>Output Buffer Frames</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
        {images.map((base64, index) => (
          <img
            key={index}
            src={`data:image/jpeg;base64,${base64}`}
            alt={`frame-${index}`}
            style={{ maxWidth: "300px", border: "1px solid #ccc" }}
          />
        ))}
        {images.length === 0 && <p>No frames available</p>}
      </div>
    </div>
  );
}
