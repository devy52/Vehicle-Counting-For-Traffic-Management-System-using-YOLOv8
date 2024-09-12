import streamlit as st
import requests
import os
import moviepy.editor as mp
from io import BytesIO
import base64

# Function to remove audio from the video
def remove_audio(input_file, output_file):
    try:
        video = mp.VideoFileClip(input_file)
        video_without_audio = video.without_audio()
        video_without_audio.write_videofile(output_file, codec='libx264', fps=video.fps)
        return video_without_audio.duration
    except Exception as e:
        st.error(f"Error removing audio: {e}")
        return None

# URL for your Flask backend
PUBLIC_URL = "https://4718-34-91-191-201.ngrok-free.app"  # Replace with your ngrok URL

# Function to process the video
def process_video(video_file):
    st.success("Video Uploaded. Processing...")
    
    with st.spinner('Processing video...'):
        response = requests.post(PUBLIC_URL + '/process_video', files={'video': video_file})
        
    if response.status_code == 200:
        result = response.json()
        video_url = result.get('video_url')
        total_count = result.get('count')
        frequency_data = result.get('frequency_data')
        return video_url, total_count, frequency_data
    else:
        st.error(f"Error processing video: {response.json().get('error')}")
        return None, None, None

# Function to download and save the video
def download_and_save_video(video_url, save_folder="temp"):
    video_response = requests.get(PUBLIC_URL + video_url, stream=True)
    if video_response.status_code == 200:
        os.makedirs(save_folder, exist_ok=True)
        video_path = os.path.join(save_folder, os.path.basename(video_url))
        with open(video_path, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return video_path
    else:
        st.error("Failed to download video.")
        return None

# Convert BytesIO to Data URL
def bytesio_to_dataurl(bytesio_obj, mime_type):
    binary_data = bytesio_obj.getvalue()
    base64_data = base64.b64encode(binary_data).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_data}"
    return data_url

# Streamlit UI
st.title("Vehicle Counting System for Traffic Management")

# File uploader for video upload
video_file = st.file_uploader("Upload Video", type=["mp4", "avi"])

if video_file:
    video_url, total_count, frequency_data = process_video(video_file)
    if video_url:
        st.write(f"Total Vehicles Count: {total_count}")
        
        # Download and save the video in the temp folder
        local_video_path = download_and_save_video(video_url)
        if local_video_path:
            no_audio_video_path = 'temp/' + os.path.basename(local_video_path) + '_no_audio.mp4'
            video_duration = remove_audio(local_video_path, no_audio_video_path)

            if video_duration:
                # Open the processed video file as BytesIO for conversion
                with open(no_audio_video_path, "rb") as video_file_obj:
                    video_bytesio = BytesIO(video_file_obj.read())
                
                # Convert the processed video (BytesIO) to a Data URL
                video_data_url = bytesio_to_dataurl(video_bytesio, "video/mp4")

                # Convert frequency_data into JSON format for embedding into JS
                frequency_data_js = frequency_data

                # HTML and JavaScript for video and synchronized frequency display
                video_html = f"""
                <div id="container" style="width: 100%; height: 600px; overflow: auto; position: relative;">
                    <video id="myVideo" width="100%" controls>
                      <source src="{video_data_url}" type="video/mp4">
                      Your browser does not support HTML video.
                    </video>
                    <div id="frequencyData" style="position: absolute; bottom: 0; width: 100%; background: rgba(255, 255, 255, 0.8); padding: 10px; font-size: 18px; color: #333;">
                        Frequency Data will appear here
                    </div>
                </div>

                <script>
                var video = document.getElementById('myVideo');
                var frequencyDataDiv = document.getElementById('frequencyData');
                var frequencyData = {frequency_data_js};  // Insert frequency data as JS array

                // Function to update frequency data based on video time
                function updateFrequencyData() {{
                    var currentTime = Math.floor(video.currentTime);
                    var frequencyIndex = Math.floor(currentTime / 5);
                    
                    if (frequencyIndex < frequencyData.length) {{
                        frequencyDataDiv.innerHTML = "Time: " + (frequencyIndex * 5) + "-" + ((frequencyIndex + 1) * 5) + " seconds: " + frequencyData[frequencyIndex] + " vehicles";
                    }} else {{
                        frequencyDataDiv.innerHTML = "End of Data";
                    }}
                }}

                // Update frequency data on timeupdate
                video.addEventListener('timeupdate', updateFrequencyData);

                // Ensure the container height adjusts to video height
                video.addEventListener('loadedmetadata', function() {{
                    var videoHeight = video.clientHeight;
                    var container = document.getElementById('container');
                    container.style.height = videoHeight + 'px';
                }});
                </script>
                """

                # Inject HTML + JS into Streamlit
                st.components.v1.html(video_html, height=600, scrolling=True)

                # Provide a download button for the user to download the processed video
                with open(no_audio_video_path, "rb") as f:
                    st.download_button(
                        label="Download Processed Video",
                        data=f,
                        file_name=os.path.basename(no_audio_video_path),
                        mime="video/mp4"
                    )
else:
    st.warning("Please upload a video file.")
