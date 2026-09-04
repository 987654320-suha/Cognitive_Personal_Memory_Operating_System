# LOCATION: backend/app/services/sync_service.py
"""
sync_service.py
===============
Core synchronization service for CogniSphere Desktop Agent.
Handles device registration, SHA-256 deduplication, incremental file updates,
and memory pipeline integration.
"""

from __future__ import annotations
import os
import json
import uuid
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.sync_device import SyncDevice
from app.models.indexed_file import IndexedFile
from app.models.memory import Memory
from app.services.memory_service import ingest_uploaded_file
from app.services.database_service import refresh_memory_cache, get_all_memories
from ai.faiss_service import build_index
from ai.hybrid_search import build_bm25


def pair_device(
    device_name: str,
    os_info: str = "Windows",
    user_id: Optional[int] = None,
    pairing_code: Optional[str] = None,
    status: str = "connected",
    db: Session = None,
) -> dict:
    """
    Registers a new desktop device and issues a secure pairing token or pairing code.
    """
    device_id = str(uuid.uuid4())
    auth_token = f"cs_{secrets.token_urlsafe(32)}"
    now = datetime.now(timezone.utc).isoformat()

    device = SyncDevice(
        device_id=device_id,
        device_name=device_name or "Windows PC",
        os_info=os_info or "Windows",
        auth_token=auth_token,
        status=status,
        watched_folders=json.dumps([]),
        last_heartbeat=now,
        last_sync=None,
        created_at=now,
        user_id=user_id,
        pairing_code=pairing_code,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    print(f"[SyncService] Paired/registered device: {device.device_name} ({device_id}) [user={user_id}]")
    return {
        "device_id":    device.device_id,
        "device_name":  device.device_name,
        "auth_token":   auth_token,
        "status":       device.status,
        "pairing_code": device.pairing_code,
        "user_id":      device.user_id,
    }


def verify_device_token(device_id: str, auth_token: str, db: Session) -> Optional[SyncDevice]:
    """Validates the device credentials."""
    if not device_id or not auth_token:
        return None
    return db.query(SyncDevice).filter(
        SyncDevice.device_id == device_id,
        SyncDevice.auth_token == auth_token,
    ).first()


def update_heartbeat(
    device_id: str,
    status: str,
    watched_folders: Optional[List[dict]],
    db: Session,
) -> bool:
    """Updates device heartbeat, status, and folder watch states."""
    device = db.query(SyncDevice).filter(SyncDevice.device_id == device_id).first()
    if not device:
        return False

    device.last_heartbeat = datetime.now(timezone.utc).isoformat()
    if status:
        device.status = status
    if watched_folders is not None:
        device.watched_folders = json.dumps(watched_folders)

    db.commit()
    return True


def sync_file_record(
    device_id: str,
    relative_path: str,
    filename: str,
    sha256_hash: str,
    file_modified_at: str,
    file_bytes: bytes,
    db: Session,
) -> dict:
    """
    Syncs a file from desktop agent with SHA-256 deduplication and pipeline ingestion.
    """
    now = datetime.now(timezone.utc).isoformat()
    device = db.query(SyncDevice).filter(SyncDevice.device_id == device_id).first()
    user_id = device.user_id if device else None

    # 1. Content-based Deduplication Check (PHASE 8)
    # Check if identical content hash already exists with an active memory for this user
    dedup_query = db.query(IndexedFile).filter(
        IndexedFile.sha256_hash == sha256_hash,
        IndexedFile.is_deleted == False,
        IndexedFile.memory_id.isnot(None),
    )
    if user_id is not None:
        dedup_query = dedup_query.filter(IndexedFile.user_id == user_id)
    existing_file = dedup_query.first()

    if existing_file and existing_file.memory_id:
        # Check that the memory actually exists
        mem_query = db.query(Memory).filter(Memory.id == existing_file.memory_id)
        if user_id is not None:
            mem_query = mem_query.filter(Memory.user_id == user_id)
        existing_memory = mem_query.first()
        if existing_memory:
            # Re-use existing memory without redundant heavy AI parsing/embedding!
            record = db.query(IndexedFile).filter(
                IndexedFile.device_id == device_id,
                IndexedFile.relative_path == relative_path,
            ).first()

            if not record:
                record = IndexedFile(
                    device_id=device_id,
                    relative_path=relative_path,
                    filename=filename,
                    extension=Path(filename).suffix.lower(),
                    file_size=len(file_bytes),
                    sha256_hash=sha256_hash,
                    file_modified_at=file_modified_at,
                    first_indexed_at=now,
                    last_indexed_at=now,
                    sync_status="synced",
                    memory_id=existing_memory.id,
                    is_deleted=False,
                    user_id=user_id,
                )
                db.add(record)
            else:
                record.sha256_hash = sha256_hash
                record.file_size = len(file_bytes)
                record.file_modified_at = file_modified_at
                record.last_indexed_at = now
                record.sync_status = "synced"
                record.memory_id = existing_memory.id
                record.is_deleted = False
                record.user_id = user_id

            if device:
                device.last_sync = now

            db.commit()
            db.refresh(record)
            print(f"[SyncService] Deduplicated file {filename} (reused memory #{existing_memory.id}) [user={user_id}]")
            return {
                "success": True,
                "file_id": record.id,
                "memory_id": existing_memory.id,
                "deduplicated": True,
                "title": existing_memory.title,
            }

    # 2. Ingest through existing CogniSphere Pipeline
    try:
        memory_dict = ingest_uploaded_file(file_bytes, filename, user_id=user_id)
        memory_id = memory_dict.get("id")

        # Refresh in-memory cache and indices
        try:
            refresh_memory_cache()
            memories = get_all_memories(user_id=user_id)
            if memories:
                build_index(memories)
                build_bm25(memories)
        except Exception as idx_err:
            print(f"[SyncService] Index refresh warning: {idx_err}")

        # 3. Create or update IndexedFile manifest record
        record = db.query(IndexedFile).filter(
            IndexedFile.device_id == device_id,
            IndexedFile.relative_path == relative_path,
        ).first()

        if not record:
            record = IndexedFile(
                device_id=device_id,
                relative_path=relative_path,
                filename=filename,
                extension=Path(filename).suffix.lower(),
                file_size=len(file_bytes),
                sha256_hash=sha256_hash,
                file_modified_at=file_modified_at,
                first_indexed_at=now,
                last_indexed_at=now,
                sync_status="synced",
                memory_id=memory_id,
                is_deleted=False,
                user_id=user_id,
            )
            db.add(record)
        else:
            record.sha256_hash = sha256_hash
            record.file_size = len(file_bytes)
            record.file_modified_at = file_modified_at
            record.last_indexed_at = now
            record.sync_status = "synced"
            record.memory_id = memory_id
            record.is_deleted = False
            record.user_id = user_id

        # Update device last_sync
        if device:
            device.last_sync = now

        db.commit()
        db.refresh(record)

        print(f"[SyncService] Successfully synced {filename} (Memory #{memory_id}) [user={user_id}]")
        return {
            "success": True,
            "file_id": record.id,
            "memory_id": memory_id,
            "deduplicated": False,
            "title": memory_dict.get("title", filename),
        }

    except Exception as e:
        db.rollback()
        print(f"[SyncService] Ingestion failed for {filename}: {e}")
        return {
            "success": False,
            "error": str(e),
            "filename": filename,
        }


def delete_file_record(device_id: str, relative_path: str, db: Session) -> dict:
    """
    Handles file deletion: marks IndexedFile as deleted and cleans up memory if unreferenced.
    """
    record = db.query(IndexedFile).filter(
        IndexedFile.device_id == device_id,
        IndexedFile.relative_path == relative_path,
        IndexedFile.is_deleted == False,
    ).first()

    if not record:
        return {"success": False, "message": "File not found in index"}

    record.is_deleted = True
    record.sync_status = "deleted"
    record.last_indexed_at = datetime.now(timezone.utc).isoformat()
    memory_id = record.memory_id

    # Check if any other non-deleted file references this memory
    other_refs = db.query(IndexedFile).filter(
        IndexedFile.memory_id == memory_id,
        IndexedFile.is_deleted == False,
        IndexedFile.id != record.id,
    ).count()

    deleted_memory = False
    if memory_id and other_refs == 0:
        mem = db.query(Memory).filter(Memory.id == memory_id).first()
        if mem:
            db.delete(mem)
            deleted_memory = True

    db.commit()

    if deleted_memory:
        refresh_memory_cache()
        memories = get_all_memories(user_id=record.user_id)
        if memories:
            build_index(memories)
            build_bm25(memories)

    print(f"[SyncService] Deleted file record for {relative_path} (Memory deleted: {deleted_memory})")
    return {
        "success": True,
        "relative_path": relative_path,
        "memory_deleted": deleted_memory,
    }


def get_sync_overview(db: Session, user_id: Optional[int] = None) -> dict:
    """Returns overview statistics for desktop sync scoped to the given user if provided."""
    dev_query = db.query(SyncDevice)
    file_query = db.query(IndexedFile).filter(IndexedFile.is_deleted == False)

    if user_id is not None:
        dev_query = dev_query.filter(SyncDevice.user_id == user_id)
        file_query = file_query.filter(IndexedFile.user_id == user_id)

    devices = dev_query.all()
    total_files = file_query.count()

    device_list = []
    now_dt = datetime.now(timezone.utc)
    for d in devices:
        d_dict = d.to_dict()
        file_count = db.query(IndexedFile).filter(
            IndexedFile.device_id == d.device_id,
            IndexedFile.is_deleted == False,
        ).count()
        d_dict["indexed_files_count"] = file_count

        # Dynamic status check: if not paused and not pending, check heartbeat age (> 60s -> offline)
        raw_status = d.status or "connected"
        if raw_status not in ("paused", "pending_pairing"):
            if d.last_heartbeat:
                try:
                    hb_str = d.last_heartbeat.replace("Z", "+00:00")
                    hb_dt = datetime.fromisoformat(hb_str)
                    if hb_dt.tzinfo is None:
                        hb_dt = hb_dt.replace(tzinfo=timezone.utc)
                    if (now_dt - hb_dt).total_seconds() > 60:
                        d_dict["status"] = "offline"
                    else:
                        d_dict["status"] = raw_status
                except Exception:
                    d_dict["status"] = raw_status
            else:
                d_dict["status"] = "offline"
        else:
            d_dict["status"] = raw_status

        device_list.append(d_dict)

    return {
        "total_devices": len(devices),
        "total_indexed_files": total_files,
        "devices": device_list,
    }
