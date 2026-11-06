"""Local storage checks for the private Observatory spool."""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat

if os.name == "nt":
    import ctypes as ct
    from ctypes import wintypes as wt
    import msvcrt
    import re

    _kernel = ct.WinDLL("kernel32", use_last_error=True)
    _security = ct.WinDLL("advapi32", use_last_error=True)
    _DACL = 4
    _DIR_DACL = "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
    _PRIVATE_DACL = re.compile(r"D:[PAI]*(?:\(A;[OICD]*;FA;;;(?:OW|SY|BA)\)){3}")

    class _Attributes(ct.Structure):
        _fields_ = [("length", wt.DWORD), ("descriptor", wt.LPVOID), ("inherit_handle", wt.BOOL)]

    _kernel.CreateDirectoryW.argtypes = (wt.LPCWSTR, ct.POINTER(_Attributes))
    _kernel.CreateDirectoryW.restype = wt.BOOL
    _kernel.GetDriveTypeW.argtypes = (wt.LPCWSTR,)
    _kernel.GetDriveTypeW.restype = wt.UINT
    _kernel.LocalFree.argtypes = (wt.HLOCAL,)
    _kernel.LocalFree.restype = wt.HLOCAL
    _security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        wt.LPCWSTR, wt.DWORD, ct.POINTER(wt.LPVOID), ct.POINTER(wt.DWORD),
    )
    _security.GetFileSecurityW.argtypes = (wt.LPCWSTR, wt.DWORD, wt.LPVOID, wt.DWORD, ct.POINTER(wt.DWORD))
    _security.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
        wt.LPVOID, wt.DWORD, wt.DWORD, ct.POINTER(wt.LPWSTR), ct.POINTER(wt.DWORD),
    )

    def _mkdir(path):
        descriptor = wt.LPVOID()
        if not _security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            _DIR_DACL, 1, ct.byref(descriptor), None,
        ):
            raise ct.WinError(ct.get_last_error())
        try:
            attributes = _Attributes(ct.sizeof(_Attributes), descriptor, False)
            if not _kernel.CreateDirectoryW(str(path), ct.byref(attributes)):
                error = ct.get_last_error()
                if error != 183:  # Another cooperating publisher created it.
                    raise ct.WinError(error)
        finally:
            _kernel.LocalFree(descriptor)

    def _check_permissions(path, info):
        size = wt.DWORD()
        _security.GetFileSecurityW(str(path), _DACL, None, 0, ct.byref(size))
        if not 0 < size.value <= 65536:
            raise PermissionError("could not inspect private storage DACL")
        descriptor = ct.create_string_buffer(size.value)
        if not _security.GetFileSecurityW(str(path), _DACL, descriptor, size, ct.byref(size)):
            raise ct.WinError(ct.get_last_error())
        sddl = wt.LPWSTR()
        if not _security.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            descriptor, 1, _DACL, ct.byref(sddl), None,
        ):
            raise ct.WinError(ct.get_last_error())
        try:
            if not _PRIVATE_DACL.fullmatch(sddl.value):
                raise PermissionError("expected a private Observatory DACL")
            if stat.S_ISDIR(info.st_mode) and sddl.value != _DIR_DACL:
                raise PermissionError("expected protected inheritable Observatory DACL")
        finally:
            _kernel.LocalFree(ct.cast(sddl, wt.HLOCAL))

    def _lock(fd):
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

else:
    import fcntl

    def _mkdir(path):
        path.mkdir(mode=0o700, exist_ok=True)

    def _check_permissions(path, info):
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise PermissionError("expected current-user-only storage permissions")

    def _lock(fd):
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _is_redirect(info):
    return (stat.S_ISLNK(info.st_mode) or
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def storage_directory(value, *, create=False):
    """Require a dedicated private directory, outside a Git working tree."""
    path = Path(value).absolute()
    resolved = path.resolve()
    if not path.name or any(os.path.lexists(root / ".git") for root in
                            (path, *path.parents, resolved, *resolved.parents)):
        raise PermissionError("event journal must be outside Git working trees")
    if os.name == "nt" and _kernel.GetDriveTypeW(resolved.anchor) != 3:
        raise PermissionError("event journal requires a fixed local drive")
    if create:
        _mkdir(path)
    info = path.lstat()
    if _is_redirect(info) or not stat.S_ISDIR(info.st_mode):
        raise PermissionError("event journal must be a real directory")
    _check_permissions(path, info)
    return path


def _regular(path):
    info = path.lstat()
    if _is_redirect(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise PermissionError("expected a regular journal file with one link")
    _check_permissions(path, info)
    return info


@contextmanager
def private_file(path, *, write=False):
    flags = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        _regular(path)
    except FileNotFoundError:
        if not write:
            raise
    flags |= os.O_CREAT | os.O_RDWR if write else os.O_RDONLY
    fd = os.open(path, flags, 0o600)
    try:
        if not os.path.samestat(_regular(path), os.fstat(fd)):
            raise PermissionError("journal file identity changed")
        with os.fdopen(fd, "r+b" if write else "rb", closefd=False) as stream:
            yield stream
    finally:
        os.close(fd)


class LockBusy(OSError):
    pass


@contextmanager
def journal_lock(path, *, write=False):
    with private_file(path / "writer.lock", write=write) as stream:
        try:
            _lock(stream.fileno())
        except OSError as error:
            if error.errno in (errno.EAGAIN, errno.EACCES):
                raise LockBusy("event journal is busy") from None
            raise
        yield  # Descriptor close releases the OS lock, including on process exit.
