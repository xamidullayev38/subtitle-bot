import asyncio
import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_ffmpeg_path() -> str:
    """Tizimdan yoki imageio-ffmpeg dan ffmpeg dasturi yo'lini aniqlash"""
    # 1. Tizim PATH da tekshirish (masalan Linux/Ubuntu da o'rnatilgan bo'lsa)
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    
    # 2. imageio-ffmpeg kutubxonasidan tekshirish (Windows va boshqa muhitlar uchun)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.error(f"FFmpeg topilmadi: {e}")
        return "ffmpeg"

FFMPEG_BIN = get_ffmpeg_path()

async def merge_soft_subtitles(video_path: str, subtitle_path: str, output_path: str, language: str = "uzb") -> tuple[bool, str]:
    """
    Soft-subtitles (Ichki subtitr / Muxing):
    Video va audio qayta kodlanmaydi (-c copy).
    Bir necha soniyada tayyor bo'ladi.
    """
    if not os.path.exists(video_path):
        return False, f"Video fayl topilmadi: {video_path}"
    if not os.path.exists(subtitle_path):
        return False, f"Subtitr fayl topilmadi: {subtitle_path}"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-i", str(subtitle_path),
        "-c", "copy",
        "-metadata:s:s:0", f"language={language}",
        "-metadata:s:s:0", "title=Uzbek Subtitle",
        str(output_path)
    ]

    logger.info(f"FFmpeg buyrug'i ishga tushirilmoqda: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("Soft-subtitr muvaffaqiyatli biriktirildi.")
            return True, "Muvaffaqiyatli biriktirildi"
        else:
            err_msg = stderr.decode(errors="ignore") if stderr else "Noma'lum xatolik"
            logger.error(f"FFmpeg xatosi: {err_msg}")
            return False, f"FFmpeg xatosi: {err_msg[-200:]}"
    except Exception as e:
        logger.exception("Subtitrni biriktirishda istisno yuz berdi")
        return False, str(e)


async def merge_hard_subtitles(video_path: str, subtitle_path: str, output_path: str) -> tuple[bool, str]:
    """
    Hard-subtitles (Videoga yopishtirish / Burn-in / Re-encode):
    ESLATMA: Foydalanuvchi talabiga binoan ushbu bo'lim hozircha bo'sh qoldirildi.
    Kelajakda server quvvati oshirilganda (masalan, kuchli CPU/GPU o'rnatilganda)
    ushbu qism to'liq faollashtiriladi.
    """
    logger.warning("Hardcode rejimi hozircha faol emas.")
    return False, "Hardcode (Videoga to'liq yopishtirish) rejimi hozircha vaqtincha o'chirilgan. Iltimos, Soft-subtitr rejimidan foydalaning."
