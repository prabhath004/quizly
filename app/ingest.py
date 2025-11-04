from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.models import (
    FileUploadResponse, 
    FlashcardGenerationRequest,
    FlashcardGenerationResponse
)
from app.auth import get_current_user
from app.database import db
from app.config import get_settings
import logging
import openai
import base64
from typing import List, Optional

logger = logging.getLogger(__name__)

# Router setup
ingest_router = APIRouter()


async def extract_text_with_openai(file_content: bytes, filename: str) -> str:
    """Extract text from PDF and send to OpenAI for analysis"""
    try:
        settings = get_settings()
        client = openai.OpenAI(api_key=settings.openai_api_key)
        
        # Check file type
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension != 'pdf':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only PDF files are supported. Got: {file_extension}"
            )
        
        # Extract ALL text from PDF using PyMuPDF
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_content, filetype="pdf")
        raw_text = ""
        page_count = len(doc)
        
        for page in doc:
            raw_text += page.get_text() + "\n\n"
        doc.close()
        
        logger.info(f"Extracted {len(raw_text)} characters from {page_count} pages in {filename}")
        
        # If the PDF is very large, chunk it and analyze separately
        max_chars_per_chunk = 15000  # Safe limit for GPT-4o
        
        if len(raw_text) <= max_chars_per_chunk:
            # Small PDF - analyze in one go
            prompt = f"""
            Analyze this educational content from PDF "{filename}" ({page_count} pages) and extract key information for creating flashcards.
            
            Your task:
            1. Identify main concepts, topics, and themes
            2. Extract important definitions and explanations
            3. Highlight key points, facts, and summaries
            4. Note any examples, case studies, or applications
            5. Identify learning objectives or outcomes
            
            Provide a comprehensive, well-structured summary that captures ALL the important educational content.
            This summary will be used to generate flashcards, so be thorough and clear.
            
            Document content:
            {raw_text}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.2
            )
            
            analyzed_content = response.choices[0].message.content
            
        else:
            # Large PDF - split into chunks and analyze each
            chunks = [raw_text[i:i+max_chars_per_chunk] for i in range(0, len(raw_text), max_chars_per_chunk)]
            all_summaries = []
            
            for idx, chunk in enumerate(chunks, 1):
                prompt = f"""
                Analyze this section (part {idx}/{len(chunks)}) of the educational PDF "{filename}" and extract key information.
                
                Your task:
                1. Identify main concepts, topics, and themes
                2. Extract important definitions and explanations
                3. Highlight key points, facts, and summaries
                4. Note any examples, case studies, or applications
                5. Identify learning objectives or outcomes
                
                Provide a clear summary of the educational content in this section.
                
                Content:
                {chunk}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.2
                )
                
                all_summaries.append(response.choices[0].message.content)
            
            # Combine all summaries
            analyzed_content = "\n\n--- COMBINED SUMMARY ---\n\n" + "\n\n".join(all_summaries)
            logger.info(f"Analyzed {len(chunks)} chunks from large PDF")
        
        logger.info(f"OpenAI analyzed PDF {filename}: {len(analyzed_content)} characters from {len(raw_text)} raw characters")
        
        return analyzed_content
        
    except Exception as e:
        logger.error(f"PDF analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze PDF {filename}: {str(e)}"
        )


@ingest_router.post("/upload", response_model=FileUploadResponse, tags=["File Ingestion"])
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a file to Supabase Storage"""
    try:
        settings = get_settings()
        
        # Validate file size
        file_size_mb = len(await file.read()) / (1024 * 1024)
        await file.seek(0)  # Reset file pointer
        
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file_size_mb:.2f}MB exceeds maximum {settings.max_file_size_mb}MB"
            )
        
        # Upload to Supabase Storage
        file_content = await file.read()
        file_path = f"uploads/{current_user.id}/{file.filename}"
        
        # Upload file to Supabase Storage
        storage_response = db.client.storage.from_("quizly-files").upload(
            file_path,
            file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = db.client.storage.from_("quizly-files").get_public_url(file_path)
        
        return FileUploadResponse(
            file_id=file_path,  # Use file_path as ID
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            upload_url=public_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )


# Removed extract_text_from_file endpoint - redundant since generate_flashcards handles everything


# ingest.py now only handles file uploads and text extraction core function
# Flashcard generation is handled by ai.py using the extract_text_with_openai function
