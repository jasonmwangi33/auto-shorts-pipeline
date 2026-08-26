name: Batch Story Rendering Pipeline

on:
  workflow_dispatch:
    inputs:
      story_1:
        description: 'Story 1 Text'
        required: false
        type: string
      story_2:
        description: 'Story 2 Text'
        required: false
        type: string
      story_3:
        description: 'Story 3 Text'
        required: false
        type: string
      story_4:
        description: 'Story 4 Text'
        required: false
        type: string
      story_5:
        description: 'Story 5 Text'
        required: false
        type: string
      story_6:
        description: 'Story 6 Text'
        required: false
        type: string
      story_7:
        description: 'Story 7 Text'
        required: false
        type: string

jobs:
  ai-processing:
    name: 🧠 AI Story Processing
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Run Gemini AI (Stage 1)
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          STORY_1: ${{ inputs.story_1 }}
          STORY_2: ${{ inputs.story_2 }}
          STORY_3: ${{ inputs.story_3 }}
          STORY_4: ${{ inputs.story_4 }}
          STORY_5: ${{ inputs.story_5 }}
          STORY_6: ${{ inputs.story_6 }}
          STORY_7: ${{ inputs.story_7 }}
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          python pipeline/batch_router.py 1
      - name: Upload Workspace
        uses: actions/upload-artifact@v4
        with:
          name: shared-workspace
          path: workspace/
          overwrite: true

  cloud-rendering:
    name: 🎬 Cloud Rendering
    needs: ai-processing
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Download Workspace
        uses: actions/download-artifact@v4
        with:
          name: shared-workspace
          path: workspace/
      - name: Run Engine (Stage 2)
        env:
          PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          python pipeline/batch_router.py 2
      - name: Upload Workspace
        uses: actions/upload-artifact@v4
        with:
          name: shared-workspace
          path: workspace/
          overwrite: true

  publishing:
    name: 🚀 Auto-Publishing
    needs: cloud-rendering
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Download Workspace
        uses: actions/download-artifact@v4
        with:
          name: shared-workspace
          path: workspace/
      - name: Run Publisher & Uploader (Stage 3)
        env:
          YOUTUBE_ACCOUNTS_JSON: ${{ secrets.YOUTUBE_ACCOUNTS_JSON }}
          YTDLP_COOKIES_CONTENT: ${{ secrets.YTDLP_COOKIES_CONTENT }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          python pipeline/batch_router.py 3
