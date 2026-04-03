# Storage Integration (obstore)

## Overview

Advanced Alchemy provides a `FileObject` type and `StoredObject` SQLAlchemy column type for managing file metadata alongside database records. Files are stored in external backends (S3, GCS, Azure, local filesystem) via the `obstore` or `fsspec` libraries, while metadata (filename, size, content type, etag, etc.) is persisted as JSONB in the database.

Key components:

- `FileObject` -- represents file metadata and provides save/delete/sign operations
- `StoredObject` -- SQLAlchemy `TypeDecorator` that serializes `FileObject` to/from JSONB
- `StorageBackend` -- abstract base for backend implementations
- `ObstoreBackend` -- backend using the `obstore` library (default when installed)
- `FSSpecBackend` -- backend using `fsspec` (fallback)
- `StorageRegistry` -- singleton registry for named backend instances
- `FileObjectSessionTracker` -- tracks pending file operations per session transaction

Install:

```bash
pip install advanced-alchemy[obstore]   # preferred
pip install advanced-alchemy[fsspec]    # alternative
```

---

## Storage Backend Registration

Before using `FileObject` or `StoredObject`, register one or more storage backends:

```python
from advanced_alchemy.types.file_object import storages
from advanced_alchemy.types.file_object.backends.obstore import ObstoreBackend
```

### Local Filesystem

```python
from obstore.store import LocalStore

backend = ObstoreBackend(
    key="local",
    fs=LocalStore(prefix="/data/uploads"),
)
storages.register_backend(backend)
```

### Amazon S3

```python
from obstore.store import S3Store

backend = ObstoreBackend(
    key="s3-uploads",
    fs=S3Store(
        bucket="my-app-uploads",
        region="us-east-1",
    ),
)
storages.register_backend(backend)
```

### Google Cloud Storage

```python
from obstore.store import GCSStore

backend = ObstoreBackend(
    key="gcs-uploads",
    fs=GCSStore(bucket="my-app-uploads"),
)
storages.register_backend(backend)
```

### Azure Blob Storage

```python
from obstore.store import AzureStore

backend = ObstoreBackend(
    key="azure-uploads",
    fs=AzureStore(
        container="uploads",
        account_name="myaccount",
    ),
)
storages.register_backend(backend)
```

### From URL (Auto-Detect)

The `ObstoreBackend` can auto-detect the store type from a URL:

```python
backend = ObstoreBackend(key="uploads", fs="s3://my-bucket")
storages.register_backend(backend)
```

### String Shorthand

Register a URL string directly -- the registry uses the default backend class:

```python
storages.register_backend("s3://my-bucket/uploads", key="uploads")
```

---

## FSSpec Backend (Alternative)

When `obstore` is not installed or for protocols not supported by obstore, use the `fsspec` backend:

```python
from advanced_alchemy.types.file_object.backends.fsspec import FSSpecBackend

backend = FSSpecBackend(
    key="gcs-data",
    fs="gcs",  # protocol string -- fsspec resolves to gcsfs
    prefix="my-bucket/data",
    token="google_default",
)
storages.register_backend(backend)
```

The `FSSpecBackend` supports a `prefix` parameter that is prepended to all paths. It auto-detects whether the underlying filesystem supports async operations and uses `asyncio.to_thread()` for sync-only filesystems.

---

## StorageRegistry

The `StorageRegistry` is a process-wide singleton:

```python
from advanced_alchemy.types.file_object import storages

# Register
storages.register_backend(backend)

# Retrieve
backend = storages.get_backend("s3-uploads")

# Check
storages.is_registered("s3-uploads")  # True

# List all
storages.registered_backends()  # ["local", "s3-uploads", ...]

# Remove
storages.unregister_backend("s3-uploads")

# Clear all
storages.clear_backends()
```

The default backend class is `ObstoreBackend` when `obstore` is installed, otherwise `FSSpecBackend`.

---

## FileObject

`FileObject` represents a file's metadata and provides methods for content access, saving, deletion, and URL signing.

### Creating a FileObject

```python
from advanced_alchemy.types.file_object import FileObject

# With pending content (saved later by session tracker or explicit save)
avatar = FileObject(
    backend="s3-uploads",
    filename="avatars/user123.jpg",
    content=uploaded_bytes,
    content_type="image/jpeg",
    metadata={"user_id": "123", "original_name": "photo.jpg"},
)

# With pending source path
document = FileObject(
    backend="local",
    filename="documents/report.pdf",
    source_path="/tmp/uploaded_report.pdf",
    content_type="application/pdf",
)

# Metadata-only (file already exists in storage)
existing = FileObject(
    backend="s3-uploads",
    filename="documents/report.pdf",
    size=1048576,
    content_type="application/pdf",
    etag="abc123",
)
```

You cannot provide both `content` and `source_path` -- pick one.

### Properties

| Property | Type | Description |
|---|---|---|
| `filename` / `path` | `str` | The storage path (uses `to_filename` if set) |
| `backend` | `StorageBackend` | Resolved backend instance |
| `content_type` | `str` | MIME type (auto-guessed from filename if not set) |
| `protocol` | `str` | Backend protocol (`s3`, `gcs`, `file`, etc.) |
| `size` | `int \| None` | File size in bytes |
| `etag` | `str \| None` | Entity tag for cache validation |
| `last_modified` | `float \| None` | Last modification timestamp |
| `checksum` | `str \| None` | File checksum |
| `version_id` | `str \| None` | Object version identifier |
| `metadata` | `dict[str, Any]` | Custom metadata key-value pairs |
| `has_pending_data` | `bool` | Whether content/source_path is pending save |

### Content Operations

```python
# Read content
content: bytes = file_obj.get_content()
content: bytes = await file_obj.get_content_async()

# Save (explicit)
file_obj.save(data=b"file contents")
await file_obj.save_async(data=b"file contents")

# Save pending content (set during init)
file_obj.save()
await file_obj.save_async()

# Delete from storage
file_obj.delete()
await file_obj.delete_async()
```

### Multipart Upload Options

```python
await file_obj.save_async(
    data=large_file_bytes,
    use_multipart=True,
    chunk_size=10 * 1024 * 1024,  # 10MB chunks
    max_concurrency=8,
)
```

### Serialization

```python
# To dict (for JSON serialization)
data = file_obj.to_dict()
# {"filename": "...", "backend": "s3-uploads", "content_type": "...", ...}

# Update metadata
file_obj.update_metadata({"processed": True, "dimensions": "800x600"})
```

---

## Presigned URL Generation

Both `ObstoreBackend` and (partially) `FSSpecBackend` support signed URL generation:

```python
# Download URL (default 1 hour expiry)
download_url = file_obj.sign()
download_url = await file_obj.sign_async()

# With custom expiry
download_url = file_obj.sign(expires_in=3600)

# Upload URL (presigned PUT)
upload_url = file_obj.sign(for_upload=True, expires_in=900)
upload_url = await file_obj.sign_async(for_upload=True, expires_in=900)
```

**Note**: `FSSpecBackend` does not support `for_upload=True` -- use `ObstoreBackend` for presigned upload URLs.

---

## StoredObject Column Type

`StoredObject` is a SQLAlchemy `TypeDecorator` that stores `FileObject` metadata as JSONB. It handles serialization/deserialization and backend resolution transparently.

### Single File Column

```python
from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.types.file_object import FileObject, StoredObject
from sqlalchemy.orm import Mapped, mapped_column

class UserProfile(UUIDAuditBase):
    __tablename__ = "user_profile"

    name: Mapped[str]
    avatar: Mapped[FileObject | None] = mapped_column(
        StoredObject(backend="s3-uploads"),
        default=None,
    )
```

### Multiple Files Column

```python
from advanced_alchemy.types.file_object import FileObject, FileObjectList, StoredObject

class Document(UUIDAuditBase):
    __tablename__ = "document"

    title: Mapped[str]
    attachments: Mapped[FileObjectList | None] = mapped_column(
        StoredObject(backend="s3-uploads", multiple=True),
        default=None,
    )
```

`FileObjectList` is a `MutableList[FileObject]` that tracks mutations for the session tracker.

### How It Works

- **On write** (`process_bind_param`): Calls `FileObject.to_dict()` to produce a JSON-serializable dict. For `multiple=True`, produces a list of dicts.
- **On read** (`process_result_value`): Reconstructs `FileObject` instances from the stored JSON. The `backend` key is resolved via the `StorageRegistry`.

---

## Automatic File Lifecycle (Session Tracker)

AA registers session event listeners that coordinate file operations with database transactions:

### Behavior

1. **Before flush**: `FileObjectInspector` scans new, dirty, and deleted instances for `StoredObject` columns. Pending saves and deletes are queued in the `FileObjectSessionTracker`.
2. **After commit**: Pending saves are executed (files written to storage), then pending deletes are executed (old files removed from storage).
3. **After rollback**: Files saved during the rolled-back transaction are cleaned up from storage.

### Single File Lifecycle

```python
# Create with pending content
profile.avatar = FileObject(
    backend="s3-uploads",
    filename=f"avatars/{profile.id}.jpg",
    content=uploaded_bytes,
)
await session.commit()
# File is saved to S3 after commit

# Update (old file is deleted, new file is saved)
profile.avatar = FileObject(
    backend="s3-uploads",
    filename=f"avatars/{profile.id}_v2.jpg",
    content=new_bytes,
)
await session.commit()

# Delete record (file is deleted from storage)
await session.delete(profile)
await session.commit()
```

### Multiple Files Lifecycle

```python
# Append a file
doc.attachments.append(FileObject(
    backend="s3-uploads",
    filename=f"docs/{doc.id}/new_file.pdf",
    content=pdf_bytes,
))
await session.commit()

# Remove a file
removed = doc.attachments.pop(0)
await session.commit()
# Removed file is deleted from storage

# Replace entire list
doc.attachments = MutableList([
    FileObject(backend="s3-uploads", filename="docs/a.pdf", content=a_bytes),
])
await session.commit()
# Old files not in new list are deleted, new files are saved
```

### Error Handling

By default (`raise_on_error=True`), file operation failures raise exceptions. Set `raise_on_error=False` for graceful degradation:

```python
# Via session info
session.info["file_object_raise_on_error"] = False
```

### Enabling/Disabling File Listeners

```python
# Via session info
session.info["enable_file_object_listener"] = False

# Via engine execution options
engine = create_async_engine(url, execution_options={"enable_file_object_listener": False})
```

---

## Pydantic Integration

`FileObject` provides a `__get_pydantic_core_schema__` method for seamless Pydantic v2 validation and serialization:

```python
from pydantic import BaseModel
from advanced_alchemy.types.file_object import FileObject

class ProfileSchema(BaseModel):
    name: str
    avatar: FileObject | None = None
```

Pydantic validates `FileObject` from either an existing instance or a dict with `filename` and `backend` keys. Serialization uses `to_dict()`.

---

## Backend Protocol Reference

All backends implement `StorageBackend`:

| Method | Signature | Description |
|---|---|---|
| `get_content` | `(path) -> bytes` | Read file content |
| `get_content_async` | `(path) -> bytes` | Read file content (async) |
| `save_object` | `(file_object, data) -> FileObject` | Write file, update metadata |
| `save_object_async` | `(file_object, data) -> FileObject` | Write file (async) |
| `delete_object` | `(paths)` | Delete one or more files |
| `delete_object_async` | `(paths)` | Delete files (async) |
| `sign` | `(paths, expires_in, for_upload) -> str` | Generate signed URL |
| `sign_async` | `(paths, expires_in, for_upload) -> str` | Generate signed URL (async) |

### ObstoreBackend Specifics

- Uses `obstore.store.from_url()` for URL-based initialization.
- Detects store type via `schema_from_type()` (S3, GCS, Azure, Local, HTTP, Memory).
- `LocalStore` does not support attributes (content-type metadata) -- these are silently skipped.
- Metadata values are serialized to strings (obstore requirement).

### FSSpecBackend Specifics

- Accepts any `fsspec.AbstractFileSystem` or `fsspec.asyn.AsyncFileSystem` instance.
- Falls back to `asyncio.to_thread()` for sync-only filesystems.
- Supports a `prefix` parameter for path namespacing.
- Does not support `for_upload=True` in `sign()`.
