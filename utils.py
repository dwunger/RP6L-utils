import os
import struct
import os
import tkinter as tk
from tkinter import filedialog

def unpack_items(file_content, num_items, format_string, offset):
    items = []
    item_size = struct.calcsize(format_string)
    for _ in range(num_items):
        item = struct.unpack_from(format_string, file_content, offset=offset)
        items.append(item)
        offset += item_size
    return items

def InputOpenFileName(title, filter="All files (*)", filename=""):
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[(filter, filter)],
        initialfile=filename,
    )
    return file_path

def read_binary_file(file_path):
    with open(file_path, 'rb') as file:
        file_content = file.read()
    return file_content

def parse_binary_file(file_content):
    header_format = '<IIBBBBIIIIII'  # struct format for the header, '<' indicates little endian
    section_format = '<BBBBIIHH'  # struct format for the section
    filepart_format = '<BBHIII'  # struct format for the filepart
    filemap_format = '<BBBBII'  # struct format for the filemap
    fname_idx_format = '<I'  # struct format for the fname_idx

    # Parse the binary data using the defined formats
    header = struct.unpack_from(header_format, file_content)
    sections = [struct.unpack_from(section_format, file_content, offset=i*struct.calcsize(section_format)) for i in range(header.sections)]
    fileparts = [struct.unpack_from(filepart_format, file_content, offset=i*struct.calcsize(filepart_format)) for i in range(header.parts)]
    filemaps = [struct.unpack_from(filemap_format, file_content, offset=i*struct.calcsize(filemap_format)) for i in range(header.files)]
    fname_idxs = [struct.unpack_from(fname_idx_format, file_content, offset=i*struct.calcsize(fname_idx_format)) for i in range(header.files)]

    # Calculate the offset where the file names start
    filename_offset = 36 + 20 * header.sections + 16 * header.parts + header.files * (12 + 4)

    return header, sections, fileparts, filemaps, fname_idxs, filename_offset


class FileManager:
    def __init__(self):
        self.open_files = {}  # A dictionary to keep track of open files
        self.selected_file = None  # The currently selected file

    def open_file(self, file_path, mode='rb+'):
        if not os.path.exists(file_path):
            open(file_path, 'wb+').close()  # This will create a new file if it doesn't exist

        self.open_files[file_path] = open(file_path, mode)
        self.selected_file = self.open_files[file_path]
    
    def close_file(self, file_path):
        if file_path in self.open_files:
            self.open_files[file_path].close()
            del self.open_files[file_path]
            if self.selected_file == self.open_files[file_path]:
                self.selected_file = None
    
    def find_open_file(self, file_path):
        return file_path in self.open_files

    def select_file(self, file_path):
        if not self.find_open_file(file_path):
            self.open_file(file_path, 'rb+')
        self.selected_file = self.open_files[file_path]


    def insert_bytes(self, start, size, value=0):
        self.selected_file.seek(start)
        bytes_to_insert = bytes([value] * size)
        self.selected_file.write(bytes_to_insert)

    def write_uint(self, pos, value):
        data = struct.pack('<I', value)  # Use '<' for little-endian byte order (same as 010 Editor)
        self.selected_file.seek(pos)
        self.selected_file.write(data)


    def save_file_range(self, file_path, start, size):
        if not self.find_open_file(file_path):
            raise ValueError(f"File {file_path} is not open.")
        
        self.selected_file.seek(start)
        data = self.selected_file.read(size)
        
        with open(file_path, 'wb') as f:
            f.write(data)
            
    def read_ubyte(self, pos=None):
        if pos is None:
            pos = self.selected_file.tell()
        
        self.selected_file.seek(pos)
        return struct.unpack('<B', self.selected_file.read(1))[0]  # Read unsigned byte

    def read_uint(self, pos=None):
        if pos is None:
            pos = self.selected_file.tell()
        
        self.selected_file.seek(pos)
        return struct.unpack('<I', self.selected_file.read(4))[0]  # Read unsigned int

    def read_ushort(self, pos=None):
        if pos is None:
            pos = self.selected_file.tell()
        
        self.selected_file.seek(pos)
        return struct.unpack('<H', self.selected_file.read(2))[0]  # Read unsigned short

    def ftell(self):
        return self.selected_file.tell()