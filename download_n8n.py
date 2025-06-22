import pandas as pd
import requests
import os
from urllib.parse import urlparse, parse_qs

def extract_file_id(drive_url):
    """Extracts the file ID from a Google Drive URL."""
    parsed = urlparse(drive_url)
    if "id=" in drive_url:
        return parse_qs(parsed.query).get("id", [None])[0]
    elif "/d/" in drive_url:
        return parsed.path.split("/d/")[1].split("/")[0]
    return None

def download_file_from_google_drive(file_id, destination):
    """Downloads a file from Google Drive using its file ID."""
    URL = "https://drive.google.com/uc?export=download"

    session = requests.Session()
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # Handle confirmation token for large files
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            response = session.get(URL, params={'id': file_id, 'confirm': value}, stream=True)
            break

    with open(destination, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)

def main(excel_path):
    df = pd.read_excel(excel_path)

    for _, row in df.iterrows():
        file_name = row['file-name']
        drive_urls = row['google-drive-url']
        
        # Handle multiple URLs - split by common delimiters and take the last one
        if isinstance(drive_urls, str):
            # Split by common delimiters (comma, semicolon, newline, or space)
            url_list = [url.strip() for url in drive_urls.replace('\n', ',').replace(';', ',').replace(' ', ',').split(',') if url.strip()]
            drive_url = url_list[-1] if url_list else drive_urls
        else:
            drive_url = str(drive_urls) if drive_urls is not None else ""
        
        file_id = extract_file_id(drive_url)

        if file_id:
            print(f"Downloading {file_name}...")
            print(f"Using URL: {drive_url}")
            download_file_from_google_drive(file_id, f"{file_name}.json")
        else:
            print(f"Invalid URL: {drive_url}")
        
        # break

# Example usage
main("n8n-list.xlsx")
