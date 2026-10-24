"""Bounded PDF/DOCX text extraction in an isolated child; never persist documents."""
from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import threading
import zipfile

MAX_UPLOAD_BYTES = 2_000_000
MAX_TEXT = 12000
_slot = threading.BoundedSemaphore(1)


class ResumeError(ValueError):
    """A document cannot be safely processed; no parser details are exposed."""


def _extract(data, kind):
    if kind == 'pdf':
        if not data.startswith(b'%PDF-'):
            raise ResumeError('invalid_document')
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 10:
            raise ResumeError('unsupported_document')
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    elif kind == 'docx':
        if not data.startswith(b'PK\x03\x04'):
            raise ResumeError('invalid_document')
        from defusedxml.ElementTree import fromstring
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 100 or len({i.filename for i in entries}) != len(entries):
                raise ResumeError('unsupported_document')
            if sum(i.file_size for i in entries) > 4_000_000:
                raise ResumeError('document_too_complex')
            for item in entries:
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in item.filename or item.flag_bits & 1
                        or item.file_size > 2_000_000 or item.file_size > max(1, item.compress_size) * 100
                        or 'vbaproject' in item.filename.lower() or '/embeddings/' in item.filename.lower()
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ResumeError('unsupported_document')
            if '[Content_Types].xml' not in archive.namelist():
                raise ResumeError('invalid_document')
            tree = fromstring(archive.read('word/document.xml'))
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text = '\n'.join(' '.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in tree.findall('.//w:p', ns))
    else:
        raise ResumeError('unsupported_format')
    text = text.strip()
    if not text or len(text) > MAX_TEXT or len(text.encode()) > MAX_TEXT:
        raise ResumeError('empty_or_oversized_text')
    return text


def _windows_job(process):
    """Enforce a child memory ceiling; fail closed if the OS will not enforce it."""
    import ctypes
    from ctypes import wintypes
    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ['ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount']]
    class BASIC(ctypes.Structure):
        _fields_ = [('ProcessTime', ctypes.c_longlong), ('JobTime', ctypes.c_longlong), ('Flags', wintypes.DWORD),
                    ('Min', ctypes.c_size_t), ('Max', ctypes.c_size_t), ('Active', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t), ('Priority', wintypes.DWORD), ('Scheduling', wintypes.DWORD)]
    class LIMIT(ctypes.Structure):
        _fields_ = [('Basic', BASIC), ('IO', IO), ('ProcessMemory', ctypes.c_size_t), ('JobMemory', ctypes.c_size_t),
                    ('PeakProcess', ctypes.c_size_t), ('PeakJob', ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    info = LIMIT()
    info.Basic.Flags = 0x100 | 0x2000  # Process memory + terminate child on job close.
    info.ProcessMemory = 512 * 1024 * 1024
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
        if handle:
            kernel.CloseHandle(handle)
        raise ResumeError('parser_isolation_unavailable')
    return kernel, handle


def extract_resume(data: bytes, filename: str) -> str:
    if type(data) is not bytes or not 0 < len(data) <= MAX_UPLOAD_BYTES:
        raise ResumeError('file_size_limit')
    kind = Path(filename).suffix.lower().lstrip('.')
    if kind not in {'pdf', 'docx'}:
        raise ResumeError('unsupported_format')
    if not _slot.acquire(blocking=False):
        raise ResumeError('parser_busy')
    process, job = None, None
    try:
        env = {k: os.environ[k] for k in ('SYSTEMROOT', 'WINDIR', 'PATH', 'LANG') if k in os.environ}
        process = subprocess.Popen([sys.executable, '-I', '-B', str(Path(__file__).resolve()), kind],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        if os.name == 'nt':
            job = _windows_job(process)
        output, _ = process.communicate(data, timeout=12)
        if process.returncode or len(output) > 100_000:
            raise ResumeError('document_could_not_be_read')
        value = json.loads(output)
        if not value.get('ok'):
            raise ResumeError('document_could_not_be_read')
        return value['text']
    except (subprocess.TimeoutExpired, OSError, ValueError, KeyError):
        raise ResumeError('document_could_not_be_read') from None
    finally:
        if process and process.poll() is None:
            process.kill()
            process.communicate()
        if job:
            job[0].CloseHandle(job[1])
        _slot.release()


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    try:
        payload = sys.stdin.buffer.read(MAX_UPLOAD_BYTES + 1)
        if len(payload) > MAX_UPLOAD_BYTES:
            raise ResumeError('file_size_limit')
        result = {'ok': True, 'text': _extract(payload, sys.argv[1])}
    except Exception:
        result = {'ok': False}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))
