#!/usr/bin/env python3

import os
import csv
import requests
from pathlib import Path
from urllib.parse import urlparse
import time
from typing import List, Dict

# Configuration
CSV_FILE_PATH = "/home/usov/Downloads/RAG_math_books_80_more(2).csv"
DOWNLOAD_DIR = "/home/usov/myprojects/theorem/RAG_DOCUMENTS/downloaded_pdfs"
DELAY_BETWEEN_DOWNLOADS = 1  # seconds
TIMEOUT = 30  # seconds

def create_download_directory() -> None:
    """Create download directory if it doesn't exist"""
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    print(f"Download directory: {DOWNLOAD_DIR}")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit filename length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    return filename.strip()

def get_filename_from_url(url: str, title: str) -> str:
    """Generate filename from URL and title"""
    parsed_url = urlparse(url)
    
    # Try to get filename from URL
    url_filename = os.path.basename(parsed_url.path)
    if url_filename and url_filename.endswith('.pdf'):
        return sanitize_filename(url_filename)
    
    # Fallback to title
    title_filename = sanitize_filename(title) + '.pdf'
    return title_filename

def get_unique_filename(filepath: str) -> str:
    """Get unique filename by adding number suffix if file exists"""
    if not os.path.exists(filepath):
        return filepath
    
    base_path = os.path.splitext(filepath)[0]
    extension = os.path.splitext(filepath)[1]
    
    counter = 1
    while True:
        new_filepath = f"{base_path}_{counter}{extension}"
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

def download_pdf(url: str, filepath: str) -> bool:
    """Download PDF from URL to filepath"""
    try:
        print(f"Downloading: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT, stream=True)
        response.raise_for_status()
        
        # Check if content is actually a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            print(f"Warning: Content type is {content_type}, not PDF")
        
        # Download file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        print(f"Downloaded: {filepath} ({file_size} bytes)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error downloading {url}: {e}")
        return False

def read_csv_file() -> List[Dict[str, str]]:
    """Read CSV file and return list of dictionaries"""
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

def main():
    """Main function"""
    print("PDF Downloader Script")
    print("=" * 50)
    
    # Create download directory
    create_download_directory()
    
    # Read CSV file
    print(f"Reading CSV file: {CSV_FILE_PATH}")
    data = read_csv_file()
    
    if not data:
        print("No data found in CSV file")
        return
    
    print(f"Found {len(data)} entries in CSV")
    
    # Download PDFs
    successful_downloads = 0
    failed_downloads = 0
    
    for i, row in enumerate(data, 1):
        url = row.get('url', '').strip()
        title = row.get('title', '').strip()
        
        if not url:
            print(f"Row {i}: No URL found")
            failed_downloads += 1
            continue
        
        if not title:
            title = f"document_{i}"
        
        # Generate filename
        filename = get_filename_from_url(url, title)
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        # Get unique filename if file already exists
        filepath = get_unique_filename(filepath)
        filename = os.path.basename(filepath)
        
        # Download PDF
        print(f"\n[{i}/{len(data)}] Processing: {title}")
        if download_pdf(url, filepath):
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Delay between downloads
        if i < len(data):
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
    
    # Summary
    print("\n" + "=" * 50)
    print("Download Summary:")
    print(f"Total entries: {len(data)}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"Download directory: {DOWNLOAD_DIR}")

if __name__ == "__main__":
    main()