import os
from config import FILES_DIR

def save_uploaded_file(upload_file, save_name):
    file_path = os.path.join(FILES_DIR, save_name)
    with open(file_path, "wb") as f:
        f.write(upload_file)
    return file_path
