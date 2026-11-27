"""Read the public reference as one bounded zstd stream with the Windows inbox libarchive."""
import ctypes
import hashlib
import json
import os
from pathlib import Path


BASE = Path(__file__).resolve().parent
NAME = "compact-solution.ndjson"
PUBLIC_SIZE = 5_172_274_528
PUBLIC_SHA = "ab7b4223b9bd748a1aa68bdb63afb6d6264121fc834aadba7ba3d3796c32115b"
CHECKED_DLL = "24c23d001e869bc7e7a3011c49555e4d1fcc0f650d59b3b78eeca5fbc120d665"


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    compressed = BASE / (NAME + ".zst")
    raw = BASE / NAME
    temp = BASE / (NAME + ".unpacking")
    if raw.exists():
        raise FileExistsError(raw.name)
    library = Path(os.environ["SystemRoot"]) / "System32/archiveint.dll"
    if digest(library) != CHECKED_DLL:
        raise ValueError("The library differs from the verified Microsoft Windows file")
    dll = ctypes.CDLL(str(library), winmode=0x800)
    ptr = ctypes.c_void_p
    integer = ctypes.c_int
    size = ctypes.c_size_t

    def function(name, result, *parameters):
        fn = getattr(dll, name)
        fn.restype = result
        fn.argtypes = list(parameters)
        return fn

    new = function("archive_read_new", ptr)
    free = function("archive_read_free", integer, ptr)
    zstd = function("archive_read_support_filter_zstd", integer, ptr)
    single = function("archive_read_support_format_raw", integer, ptr)
    open_file = function("archive_read_open_filename_w", integer, ptr, ctypes.c_wchar_p, size)
    next_header = function("archive_read_next_header", integer, ptr, ctypes.POINTER(ptr))
    read = function("archive_read_data", ctypes.c_ssize_t, ptr, ptr, size)
    message = function("archive_error_string", ctypes.c_char_p, ptr)
    archive = new()
    if not archive:
        raise MemoryError("archive_read_new")

    def require(status, expected=0):
        if status != expected:
            raise ValueError((status, message(archive)))

    checksum = hashlib.sha256()
    count = 0
    buf = ctypes.create_string_buffer(1 << 20)
    view = memoryview(buf).cast("B")
    try:
        require(zstd(archive))
        require(single(archive))
        require(open_file(archive, str(compressed), len(buf)))
        entry = ptr()
        require(next_header(archive, ctypes.byref(entry)))
        with temp.open("xb") as out:
            while True:
                n = read(archive, buf, len(buf))
                if n < 0:
                    raise ValueError(message(archive))
                if n == 0:
                    break
                count += n
                if count > PUBLIC_SIZE:
                    raise ValueError("exceeded the published uncompressed size")
                block = view[:n]
                checksum.update(block)
                out.write(block)
        require(next_header(archive, ctypes.byref(entry)), 1)
    finally:
        free(archive)
    if count != PUBLIC_SIZE or checksum.hexdigest() != PUBLIC_SHA:
        raise ValueError(("reference checksum mismatch", count, checksum.hexdigest()))
    temp.rename(raw)
    result = {
        "url": "https://math.mit.edu/~drew/shortgrh/compact-solution.ndjson.zst",
        "publicChecksums": "https://math.mit.edu/~drew/shortgrh/exports.sha256",
        "compressedBytes": compressed.stat().st_size,
        "compressedSha256": digest(compressed),
        "rawBytes": count,
        "rawSha256": checksum.hexdigest(),
        "matchesPublishedRawSha256": True,
        "decoder": "Microsoft Windows archiveint.dll/libarchive 3.8.9",
        "decoderAuthenticode": "Valid (Microsoft Windows)",
        "decoderSha256": CHECKED_DLL,
    }
    (BASE / "reference-receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(count, checksum.hexdigest())


if __name__ == "__main__":
    main()
