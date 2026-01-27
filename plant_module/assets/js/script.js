let videoStream = null;

function switchTab(mode) {
    // Hide all sections
    document.querySelectorAll('.mode-section').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tabs button').forEach(el => el.classList.remove('active'));

    // Show selected
    document.getElementById('section-' + mode).classList.remove('hidden');
    document.getElementById('tab-' + mode).classList.add('active');

    if (mode === 'webcam') startWebcam();
    else stopWebcam();
}

function startWebcam() {
    const video = document.getElementById('video');
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                videoStream = stream;
                video.srcObject = stream;
            })
            .catch(err => console.error("Camera Error:", err));
    }
}



function stopWebcam() {
    const video = document.getElementById('video');

    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
        video.srcObject = null; // clears camera preview
    }
}


function captureWebcam() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    
    // Draw video frame to canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    // Convert to Base64
    const dataURL = canvas.toDataURL('image/jpeg');
    sendData(dataURL, 'webcam');
}

function uploadImage() {
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) return alert("Please select a file!");
    
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    
    postData(formData);
}

function sendData(base64Data, type) {
    const formData = new FormData();
    formData.append("webcam_image", base64Data);
    postData(formData);
}

function postData(formData) {
    // Show loading state
    document.getElementById('result-container').classList.remove('hidden');
    document.getElementById('res-name').innerText = "Identifying...";
    
    fetch('/identify', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if(data.error) {
            alert(data.error);
        } else {
            document.getElementById('result-img').src = data.image_url;
            document.getElementById('res-name').innerText = data.plant_name;
            document.getElementById('res-prob').innerText = data.probability;
        }
    })
    .catch(error => console.error('Error:', error));
}


const video = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const resultDiv = document.getElementById('result');

// Start webcam
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
  })
  .catch(err => console.error("Webcam error:", err));

function captureWebcam() {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to blob
    canvas.toBlob(blob => {
        const formData = new FormData();
        formData.append('file', blob, 'plant.jpg');

        fetch('/plant/identify', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if(data.error){
                resultDiv.innerHTML = `<p style="color:red;">${data.error}</p>`;
            } else {
                resultDiv.innerHTML = `
                    <p><b>Scientific Name:</b> ${data.scientific}</p>
                    <p><b>Local Name:</b> ${data.local}</p>
                    <p><b>Accuracy:</b> ${data.accuracy}%</p>
                    <img src="${data.image}" width="200"/>
                `;
            }
        })
        .catch(err => console.error(err));
    }, 'image/jpeg');
}

