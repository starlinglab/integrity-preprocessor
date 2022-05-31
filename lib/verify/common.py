def sha256sum(filename):
    hasher = hashlib.sha256()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(32 * 1024), b""):
            hasher.update(byte_block)
        return hasher.hexdigest()
