#!/usr/bin/env python3
"""
Script to prepare files for AWS S3 upload.
This script helps organize and check which files need to be uploaded to S3.
"""

import os
import shutil
from pathlib import Path

def main():
    print("🚀 Preparing files for AWS S3 upload...")
    
    # Create a staging directory
    staging_dir = Path("aws_upload_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()
    
    # Files to copy from public folder
    public_dir = Path("public")
    
    if not public_dir.exists():
        print("❌ Error: 'public' directory not found!")
        return
    
    essential_files = [
        "index.html",
        "main.js",
        "consent.js", 
        "pre_surveys.js",
        "post_surveys.js",
        "preload.js",
        "slide_numbers.js",
        "meriel.css"
    ]
    
    essential_dirs = [
        "jspsych",
        "plugins", 
        "lib",
        "img"
    ]
    
    print("\n📁 Copying essential files...")
    
    # Copy files
    for file_name in essential_files:
        src = public_dir / file_name
        if src.exists():
            dst = staging_dir / file_name
            shutil.copy2(src, dst)
            print(f"✅ Copied: {file_name}")
        else:
            print(f"⚠️  Missing: {file_name}")
    
    # Copy directories
    for dir_name in essential_dirs:
        src = public_dir / dir_name
        if src.exists():
            dst = staging_dir / dir_name
            shutil.copytree(src, dst)
            print(f"✅ Copied directory: {dir_name}")
        else:
            print(f"⚠️  Missing directory: {dir_name}")
    
    print(f"\n📦 Files prepared in: {staging_dir.absolute()}")
    print("\n🔗 Next steps:")
    print("1. Follow the AWS_DEPLOYMENT_GUIDE.md")
    print("2. Create your S3 bucket and Lambda functions")
    print("3. Get your API Gateway URLs")
    print("4. Update the URLs in main.js (see note below)")
    print(f"5. Upload all files from {staging_dir} to your S3 bucket root")
    
    print("\n⚠️  IMPORTANT: Don't forget to update the API URLs in main.js!")
    print("   Look for these lines around line 199-200:")
    print("   const GET_PARTICIPANT_ID_URL = 'https://...'")
    print("   const SAVE_DATA_URL = 'https://...'")

if __name__ == "__main__":
    main()
