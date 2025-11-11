from fastapi import APIRouter, Depends, HTTPException, status
from app.models import Folder, FolderCreate, FolderUpdate
from app.auth import get_current_user
from app.database import db
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Router setup
folders_router = APIRouter()


@folders_router.post("", response_model=Folder, tags=["Folders"])
async def create_folder(
    folder_data: FolderCreate,
    current_user = Depends(get_current_user)
):
    """Create a new folder"""
    try:
        print(f"Creating folder: {folder_data.name} for user: {current_user.id}")
        
        # Create folder using service client
        result = db.service_client.table("folders").insert({
            "user_id": current_user.id,
            "name": folder_data.name,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        folder = result.data[0] if result.data else None
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create folder"
            )
        
        folder["deck_count"] = 0
        print(f"Folder created: {folder['id']}")
        
        return folder
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create folder error: {e}")
        logger.error(f"Create folder error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create folder"
        )


@folders_router.get("/my-folders", tags=["Folders"])
async def get_my_folders(current_user = Depends(get_current_user)):
    """Get all folders for current user"""
    try:
        print(f"Fetching folders for user: {current_user.id}")
        
        # Use service client to bypass RLS
        folders_result = db.service_client.table("folders").select("*").eq("user_id", current_user.id).execute()
        folders = folders_result.data if folders_result.data else []
        
        print(f"Found {len(folders)} folders")
        
        # Add deck count to each folder
        for folder in folders:
            decks_result = db.service_client.table("decks").select("*").eq("folder_id", folder["id"]).execute()
            decks = decks_result.data if decks_result.data else []
            folder["deck_count"] = len(decks)
            print(f"  Folder '{folder['name']}': {len(decks)} decks")
        
        return folders
    
    except Exception as e:
        print(f"Get folders error: {e}")
        logger.error(f"Get folders error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve folders"
        )


@folders_router.put("/{folder_id}", tags=["Folders"])
async def update_folder(
    folder_id: str,
    folder_update: FolderUpdate,
    current_user = Depends(get_current_user)
):
    """Update a folder"""
    try:
        print(f"Updating folder: {folder_id}")
        
        # Check if folder exists and belongs to user
        folder_result = db.service_client.table("folders").select("*").eq("id", folder_id).execute()
        folder = folder_result.data[0] if folder_result.data else None
        
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        if folder["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Prepare update data
        update_data = {}
        if folder_update.name is not None:
            update_data["name"] = folder_update.name
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Update folder
        result = db.service_client.table("folders").update(update_data).eq("id", folder_id).execute()
        updated_folder = result.data[0] if result.data else None
        
        if not updated_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update folder"
            )
        
        # Add deck count
        decks_result = db.service_client.table("decks").select("*").eq("folder_id", folder_id).execute()
        decks = decks_result.data if decks_result.data else []
        updated_folder["deck_count"] = len(decks)
        
        print(f"Folder updated: {folder_id}")
        return updated_folder
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update folder error: {e}")
        logger.error(f"Update folder error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update folder"
        )


@folders_router.delete("/{folder_id}", tags=["Folders"])
async def delete_folder(folder_id: str, current_user = Depends(get_current_user)):
    """Delete a folder and move its decks to root (no folder)"""
    try:
        print(f"Deleting folder: {folder_id} for user: {current_user.id}")
        
        # Check if folder exists
        folder_result = db.service_client.table("folders").select("*").eq("id", folder_id).execute()
        folder = folder_result.data[0] if folder_result.data else None
        
        if not folder:
            print(f"Folder not found: {folder_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found"
            )
        
        if folder["user_id"] != current_user.id:
            print("Folder doesn't belong to user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Move all decks in this folder to root (set folder_id to null and clear order_index)
        print("Moving decks to root...")
        try:
            # Try to update both folder_id and order_index
            db.service_client.table("decks").update({
                "folder_id": None,
                "order_index": None
            }).eq("folder_id", folder_id).execute()
        except Exception as e:
            # If order_index column doesn't exist, just update folder_id
            error_str = str(e)
            if "order_index" in error_str or "42703" in error_str:
                logger.warning("order_index column not found - moving decks without clearing order_index")
                db.service_client.table("decks").update({"folder_id": None}).eq("folder_id", folder_id).execute()
            else:
                raise
        
        # Delete folder using service client
        print("Deleting folder...")
        db.service_client.table("folders").delete().eq("id", folder_id).execute()
        
        print("Folder deleted successfully")
        
        return {"message": "Folder deleted successfully", "folder_id": folder_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete folder error: {e}")
        logger.error(f"Delete folder error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete folder"
        )
