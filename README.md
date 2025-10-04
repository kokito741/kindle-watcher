#  Kindle Notes to Google Drive

[![CI/CD Pipeline](https://github.com/kokito741/kindle-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/kokito741/kindle-watcher/actions/workflows/ci.yml)

A small service that:
- watches Gmail for Kindle emails with label `skribe`
- downloads the Kindle PDF
- uploads it to Google Drive
- optionally sends a Pushover notification

# Quick setup (local)
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```
## Install dependencies
```bash
pip install -r requirements.txt
```
## Configure environment
```bash
cp .env.example .env
```
Fill in: 
```ini
DRIVE_FOLDER_ID=your_google_drive_folder_id
PUSHOVER_TOKEN=your_pushover_app_token
PUSHOVER_USER=your_pushover_user_key
DOWNLOAD_FOLDER=./downloads
LOG_FILE=kindle_watcher.log
```
## Set up Google OAuth

1. Go to Google Cloud Console
2. Enable Gmail API and Google Drive API.
3. Create OAuth 2.0 credentials (Desktop app) and download credentials.json into the project folder.
4. Run once to generate a token: 
```bash
python main.py
```
A browser will open → grant permissions → token.json will be saved locally.
## Run service
```bash
python main.py     # start service
tail -f kindle_watcher.log   # watch logs
```
#  Quick Setup (Docker)
Run inside an isolated container.(Befire running docker image do "Set up Google OAuth"  and "Configure environment" steps)
## Clone repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```
## Build image
```bash
docker build -t kindle-watcher .
```
## Run container
```bash
docker run -d \
  --name kindle-watcher \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/token.json:/app/token.json \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/kindle_watcher.log:/app/kindle_watcher.log \
  --env-file .env \
  kindle-watcher
```
