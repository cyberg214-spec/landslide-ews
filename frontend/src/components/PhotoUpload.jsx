import { useState, useRef } from 'react';

const PhotoUpload = ({ onUploaded }) => {
  const [open, setOpen] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [location, setLocation] = useState(null);
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('crack');
  const [reporter, setReporter] = useState('');
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');

  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);

  // Open the modal
  const openModal = () => {
    setOpen(true);
    setPhoto(null);
    setDescription('');
    setCategory('crack');
    setStatus('');
    getLocation();
  };

  // Close modal
  const closeModal = () => {
    setOpen(false);
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
    }
    setCameraActive(false);
  };

  // Get GPS location
  const getLocation = () => {
    if (!navigator.geolocation) {
      setStatus('❌ GPS not supported');
      return;
    }
    setStatus('📍 Getting location...');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
        setStatus('✅ Location captured');
      },
      (err) => {
        setStatus('❌ Location failed: ' + err.message);
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  // Start camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      videoRef.current.srcObject = stream;
      videoRef.current.play();
      setCameraActive(true);
    } catch (err) {
      setStatus('❌ Camera failed: ' + err.message);
    }
  };

  // Capture from camera
  const captureFromCamera = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    setPhoto(dataUrl);

    // Stop camera
    if (video.srcObject) {
      video.srcObject.getTracks().forEach((t) => t.stop());
    }
    setCameraActive(false);
  };

  // Handle file upload
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setPhoto(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Upload
  const handleUpload = async () => {
    if (!photo) {
      setStatus('❌ Please capture or select a photo');
      return;
    }
    if (!location) {
      setStatus('❌ Please wait for GPS location');
      return;
    }
    if (!description.trim()) {
      setStatus('❌ Please add a description');
      return;
    }

    setUploading(true);
    setStatus('📤 Uploading...');

    try {
      const res = await fetch('http://localhost:8000/api/photos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lng,
          description: description.trim(),
          category: category,
          reporter: reporter.trim() || 'Anonymous',
          photo_base64: photo,
        }),
      });

      if (!res.ok) throw new Error('Upload failed');

      const data = await res.json();
      setStatus('✅ Uploaded successfully!');

      // Notify parent to refresh
      if (onUploaded) onUploaded(data);

      setTimeout(() => {
        closeModal();
      }, 1500);
    } catch (err) {
      setStatus('❌ ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      {/* Floating upload button */}
      <button className="photo-upload-btn" onClick={openModal} title="Upload photo">
        📸
      </button>

      {/* Modal */}
      {open && (
        <div className="photo-modal-backdrop" onClick={closeModal}>
          <div className="photo-modal" onClick={(e) => e.stopPropagation()}>
            <div className="photo-modal-header">
              <h2>📸 Report Incident</h2>
              <button className="photo-modal-close" onClick={closeModal}>✕</button>
            </div>

            <div className="photo-modal-body">
              {/* Photo area */}
              <div className="photo-area">
                {photo ? (
                  <img src={photo} alt="Captured" className="photo-preview-img" />
                ) : cameraActive ? (
                  <video ref={videoRef} className="photo-video" autoPlay playsInline />
                ) : (
                  <div className="photo-placeholder">
                    <span>📷</span>
                    <p>Take or upload a photo</p>
                  </div>
                )}
                <canvas ref={canvasRef} style={{ display: 'none' }} />
              </div>

              {/* Photo actions */}
              <div className="photo-actions-row">
                {!cameraActive && !photo && (
                  <>
                    <button className="photo-btn secondary" onClick={startCamera}>
                      📷 Camera
                    </button>
                    <button
                      className="photo-btn secondary"
                      onClick={() => fileInputRef.current.click()}
                    >
                      📁 Upload
                    </button>
                  </>
                )}
                {cameraActive && (
                  <button className="photo-btn primary" onClick={captureFromCamera}>
                    📸 Capture
                  </button>
                )}
                {photo && (
                  <button className="photo-btn danger" onClick={() => setPhoto(null)}>
                    🔄 Retake
                  </button>
                )}
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />

              {/* Category */}
              <div className="photo-field">
                <label>Type of Incident</label>
                <div className="category-buttons">
                  <button
                    className={`cat-btn ${category === 'crack' ? 'active' : ''}`}
                    onClick={() => setCategory('crack')}
                  >
                    🔴 Crack
                  </button>
                  <button
                    className={`cat-btn ${category === 'slope' ? 'active' : ''}`}
                    onClick={() => setCategory('slope')}
                  >
                    🟠 Slope Movement
                  </button>
                  <button
                    className={`cat-btn ${category === 'blocked' ? 'active' : ''}`}
                    onClick={() => setCategory('blocked')}
                  >
                    🟡 Blocked Road
                  </button>
                  <button
                    className={`cat-btn ${category === 'other' ? 'active' : ''}`}
                    onClick={() => setCategory('other')}
                  >
                    ⚪ Other
                  </button>
                </div>
              </div>

              {/* Description */}
              <div className="photo-field">
                <label>Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What did you see? (e.g., large crack on road near school)"
                  rows="3"
                />
              </div>

              {/* Reporter name */}
              <div className="photo-field">
                <label>Your Name (optional)</label>
                <input
                  type="text"
                  value={reporter}
                  onChange={(e) => setReporter(e.target.value)}
                  placeholder="Anonymous"
                />
              </div>

              {/* Location display */}
              <div className="photo-location">
                {location ? (
                  <>
                    📍 {location.lat.toFixed(5)}°N, {location.lng.toFixed(5)}°E
                  </>
                ) : (
                  '📍 Waiting for GPS...'
                )}
              </div>

              {/* Status */}
              {status && <div className="photo-status">{status}</div>}
            </div>

            <div className="photo-modal-footer">
              <button className="photo-btn secondary" onClick={closeModal}>
                Cancel
              </button>
              <button
                className="photo-btn primary"
                onClick={handleUpload}
                disabled={uploading || !photo || !location}
              >
                {uploading ? '⏳ Uploading...' : '📤 Upload Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default PhotoUpload;