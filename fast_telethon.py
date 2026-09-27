import asyncio
import inspect
import math
import os
from telethon.tl.types import InputFile, InputFileBig
from telethon.tl.functions.upload import (
    GetFileRequest,
    SaveBigFilePartRequest,
    SaveFilePartRequest
)

# 512 KB chunk size (Telegram tavsiya qilgan eng optimal hajm)
CHUNK_SIZE = 512 * 1024

async def _invoke_progress(callback, current, total):
    if callback:
        if inspect.iscoroutinefunction(callback):
            await callback(current, total)
        else:
            callback(current, total)

async def fast_upload(client, file_path, progress_callback=None, workers=4):
    """
    Katta fayllarni Telegramga parallel oqimlarda (Multi-connection) juda tez yuklash.
    Standart usuldan 5-10 barobar tezroq!
    """
    file_size = os.path.getsize(file_path)
    part_count = math.ceil(file_size / CHUNK_SIZE)
    is_big = file_size > 10 * 1024 * 1024  # 10 MB dan kattasi Big File hisoblanadi

    file_id = client._get_random_int()
    uploaded_bytes = 0
    lock = asyncio.Lock()

    # Har bir qism uchun vazifalar navbati
    queue = asyncio.Queue()
    for part_index in range(part_count):
        queue.put_nowait(part_index)

    async def worker():
        nonlocal uploaded_bytes
        # Alohida parallel MTProto sender ulanishi
        sender = await client._borrow_exported_sender(client.session.dc_id)
        try:
            with open(file_path, "rb") as f:
                while not queue.empty():
                    part_index = await queue.get()
                    f.seek(part_index * CHUNK_SIZE)
                    chunk = f.read(CHUNK_SIZE)
                    
                    if is_big:
                        req = SaveBigFilePartRequest(file_id, part_index, part_count, chunk)
                    else:
                        req = SaveFilePartRequest(file_id, part_index, chunk)
                    
                    await sender.send(req)
                    queue.task_done()

                    async with lock:
                        uploaded_bytes += len(chunk)
                        if progress_callback:
                            await _invoke_progress(progress_callback, uploaded_bytes, file_size)
        finally:
            await client._return_exported_sender(sender)

    worker_tasks = [asyncio.create_task(worker()) for _ in range(min(workers, part_count))]
    await queue.join()
    for task in worker_tasks:
        task.cancel()

    file_name = os.path.basename(file_path)
    if is_big:
        return InputFileBig(file_id, part_count, file_name)
    else:
        return InputFile(file_id, part_count, file_name, "")


async def fast_download(client, location, out_path, progress_callback=None, workers=4):
    """
    Katta fayllarni Telegramdan parallel oqimlarda juda tez yuklab olish.
    """
    # Agar location Message bo'lsa yoki Document bo'lsa
    if hasattr(location, "media") and location.media:
        document = getattr(location.media, "document", None)
    elif hasattr(location, "document"):
        document = location.document
    else:
        document = location

    file_size = getattr(document, "size", 0)
    if not file_size:
        # Fallback to standard client download if size is unknown
        return await client.download_media(location, file=out_path, progress_callback=progress_callback)

    part_count = math.ceil(file_size / CHUNK_SIZE)
    downloaded_bytes = 0
    lock = asyncio.Lock()

    # Bo'sh faylni kerakli hajmda yaratib olamiz
    with open(out_path, "wb") as f:
        f.truncate(file_size)

    queue = asyncio.Queue()
    for part_index in range(part_count):
        queue.put_nowait(part_index)

    from telethon.tl.types import InputDocumentFileLocation

    file_loc = InputDocumentFileLocation(
        id=document.id,
        access_hash=document.access_hash,
        file_reference=document.file_reference,
        thumb_size=""
    )

    async def worker():
        nonlocal downloaded_bytes
        sender = await client._borrow_exported_sender(document.dc_id)
        try:
            with open(out_path, "r+b") as f:
                while not queue.empty():
                    part_index = await queue.get()
                    offset = part_index * CHUNK_SIZE
                    
                    req = GetFileRequest(file_loc, offset=offset, limit=CHUNK_SIZE)
                    result = await sender.send(req)
                    chunk = result.bytes

                    f.seek(offset)
                    f.write(chunk)
                    queue.task_done()

                    async with lock:
                        downloaded_bytes += len(chunk)
                        if progress_callback:
                            await _invoke_progress(progress_callback, downloaded_bytes, file_size)
        finally:
            await client._return_exported_sender(sender)

    worker_tasks = [asyncio.create_task(worker()) for _ in range(min(workers, part_count))]
    await queue.join()
    for task in worker_tasks:
        task.cancel()

    return out_path
