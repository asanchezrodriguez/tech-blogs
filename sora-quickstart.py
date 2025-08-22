import os, time, base64, requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set environment variables or edit the corresponding values here.
endpoint = os.environ['AZURE_OPENAI_ENDPOINT']
api_key = os.environ['AZURE_OPENAI_API_KEY']

api_version = 'preview'
headers= { "api-key": api_key, "Content-Type": "application/json" }

# 1. Create a video generation job
create_url = f"{endpoint}/openai/v1/video/generations/jobs?api-version={api_version}"
body = {
    "prompt": "A cat playing piano in a jazz bar.",
    "width": 480,
    "height": 480,
    "n_seconds": 5,
    "model": "sora"
}
response = requests.post(create_url, headers=headers, json=body)
response.raise_for_status()
print("Full response JSON:", response.json())
job_id = response.json()["id"]
print(f"Job created: {job_id}")

# 2. Poll for job status
status_url = f"{endpoint}/openai/v1/video/generations/jobs/{job_id}?api-version={api_version}"
status=None
while status not in ("succeeded", "failed", "cancelled"):
    time.sleep(5)  # Wait before polling again
    status_response = requests.get(status_url, headers=headers).json()
    status = status_response.get("status")
    print(f"Job status: {status}")

# 3. Retrieve generated video 
if status == "succeeded":
    generations = status_response.get("generations", [])
    if generations:
        print(f"✅ Video generation succeeded.", generations)
        generation_id = generations[0].get("id")
        video_url = f"{endpoint}/openai/v1/video/generations/{generation_id}/content/video?api-version={api_version}"
        video_response = requests.get(video_url, headers=headers)
        if video_response.ok:
            output_filename = "output.mp4"
            # Downloading video
            print(f'Video download link {video_url}')
            # with open(output_filename, "wb") as file:
            #     file.write(video_response.content)
            #     print(f'Generated video saved as "{output_filename}"')
    else:
        raise Exception("No generations found in job result.")
else:
    raise Exception(f"Job didn't succeed. Status: {status}")
