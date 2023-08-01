from utils import InputOpenFileName, FileManager, read_binary_file, unpack_items
import os, struct
from pathlib import Path

# DDS header writer
isDXT10 = 1
bpp = 0
isCompressed = 0

DDSD_CAPS                    = 0x00000001
DDSD_HEIGHT                  = 0x00000002
DDSD_WIDTH                   = 0x00000004
DDSD_PITCH                   = 0x00000008
DDSD_PIXELFORMAT             = 0x00001000
DDSD_MIPMAPCOUNT             = 0x00020000
DDSD_LINEARSIZE              = 0x00080000
DDSD_DEPTH                   = 0x00800000

DDSCAPS_COMPLEX              = 0x00000008
DDSCAPS_TEXTURE              = 0x00001000
DDSCAPS_MIPMAP               = 0x00400000
DDSCAPS2_VOLUME              = 0x00200000
DDSCAPS2_CUBEMAP             = 0x00000200
DDSCAPS2_CUBEMAP_ALL_FACES   = 0x0000FC00

DDPF_ALPHAPIXELS             = 0x00000001
DDPF_ALPHA                   = 0x00000002
DDPF_FOURCC                  = 0x00000004
DDPF_RGB                     = 0x00000040
DDPF_NORMAL                  = 0x80000000

def compute_pitch(width, height, bpp, is_compressed):
    if is_compressed == 1:
        pitch = ((width + 3) // 4) * ((height + 3) // 4) * bpp * 2
    else:
        pitch = (width * bpp + 7) // 8
    return pitch

# This will be a global FileManager instance that we will use to keep track of opened files
fm = FileManager()

def dds_generate(width, height, mip_count, format, tex_type, depth, file_path):
    # Open file with FileManager
    fm.open_file(file_path)

    # Clear the flags and hasFOURCC variables
    flags = 0
    hasFOURCC = 0

    # Insert 128 bytes of 0 at the beginning of the file
    fm.insert_bytes( 0, 128, 0)

    # Reset these variables as we don't have corresponding definitions in this context
    isDXT10 = 0
    isCompressed = 0

    # Set the initial flags value based on the provided values
    flags = DDSD_CAPS | DDSD_PIXELFORMAT | DDSD_WIDTH | DDSD_HEIGHT | DDSD_MIPMAPCOUNT

    # Define a dictionary to map format values to bpp and flags values
    format_mapping = {
        0: 8, 1: 8, 5: 8,
        7: 16, 8: 16, 10: 16, 15: 16, 16: 16, 17: 16,
        20: 32, 21: 32, 22: 32, 32: 32, 38: 32, 39: 32, 40: 32,
        46: 64, 47: 64, 48: 64,
        59: 4, 62: 4, 63: 4,
        64: 8, 65: 8, 66: 8, 68: 8
    }

    # replace switch by mapping from dictionary
    if format in format_mapping:
        bpp = format_mapping[format]
        flags |= DDSD_PITCH
    else:
        # Handle unsupported format
        raise ValueError("Unsupported texture format detected.")

    # Check if depth is greater than 1, if yes, update flags
    if depth > 1:
        flags |= DDSD_DEPTH

    fm.write_uint(0, 542327876)  # DDS
    fm.write_uint(4, 124)  # generic headerSize
    fm.write_uint(8, flags)  # flags
    fm.write_uint(12, height)  # height
    fm.write_uint(16, width)  # width
    fm.write_uint(20, compute_pitch(width, height, bpp, isCompressed))  # pitch
    fm.write_uint(24, depth)  # depth
    fm.write_uint(28, mip_count)  # mip_count

    # reserved[11] 44 Bytes
    # ddspf
    fm.write_uint(76, 32)  # size
    flags = DDPF_FOURCC
    # use DX10 for uncompressed and except dxt1
    fm.write_uint(80, flags)  # flags

    if format == 59:
        fm.write_uint(84, 827611204)
    else:
        fm.write_uint(84, 808540228)
        fm.insert_bytes( 128, 20, 0)

    # caps
    flags = DDSCAPS_TEXTURE
    if mip_count > 1:
        flags |= DDSCAPS_COMPLEX

    if depth > 1:
        flags |= DDSCAPS_COMPLEX

    if tex_type != 0:
        flags |= DDSCAPS_COMPLEX

    fm.write_uint(108, flags)

    # caps2
    flags = 0
    if tex_type == 1:
        flags = DDSCAPS2_CUBEMAP
    elif tex_type == 2:
        flags = DDSCAPS2_VOLUME

    fm.write_uint(112, flags)

    format_conversion = {
        0: 61, 1: 63, 5: 61, 7: 56, 8: 58, 10: 59, 15: 49, 16: 51, 17: 50,
        20: 35, 21: 37, 22: 36, 32: 28, 38: 28, 39: 31, 40: 30, 46: 10,
        47: 11, 48: 13, 59: 71, 62: 81, 63: 80, 64: 84, 65: 83, 66: 95, 68: 98
    }

    # replace switch by mapping from dictionary
    if format in format_conversion:
        format = format_conversion[format]
    else:
        # Handle unsupported DDS format
        raise ValueError("Unsupported DDS format detected.")

    fm.write_uint(128, format)  # dxgiFormat
    if tex_type == 2:
        fm.write_uint(132, 4)
    else:
        fm.write_uint(132, 3)

    if tex_type == 1:
        fm.write_uint(136, 4)  # miscFlag

    fm.write_uint(140, 1)  # arraySize
    fm.close_file(file_path)

def open_file_exist(path):
    if fm.find_open_file(path):
        fm.select_file(path)
    else:
        fm.open_file(path, 'rb+')

def parse_binary_file(file_content):
    header_format = '<IIBBBBIIIIII'  # struct format for the header, '<' indicates little endian
    section_format = '<BBBBIIIHH'  # struct format for the section
    filepart_format = '<BBHIII'  # struct format for the filepart
    filemap_format = '<BBBBII'  # struct format for the filemap
    fname_idx_format = '<I'  # struct format for the fname_idx

    # Unpack the header
    header = struct.unpack_from(header_format, file_content)
    offset = struct.calcsize(header_format)  # The offset where the first section starts

    # Parse the sections
    sections = unpack_items(file_content, header[7], section_format, offset)
    offset += struct.calcsize(section_format) * header[7]

    # Parse the fileparts
    fileparts = unpack_items(file_content, header[6], filepart_format, offset)
    offset += struct.calcsize(filepart_format) * header[6]

    # Parse the filemaps
    filemaps = unpack_items(file_content, header[8], filemap_format, offset)
    offset += struct.calcsize(filemap_format) * header[8]

    # Parse the fname_idxs
    fname_idxs = unpack_items(file_content, header[10], fname_idx_format, offset)
    offset += struct.calcsize(fname_idx_format) * header[10]
    # TODO: figure out why fname_idx captures extra members. 
    # fname_idxs = fname_idxs[0:len(fileparts)]
    
    # Calculate the offset where the file names start
    filename_offset = offset

    return header, sections, fileparts, filemaps, fname_idxs, filename_offset


rpack = InputOpenFileName("Select a file to unpack", "rpack (*.rpack)")
if not rpack:
    raise ValueError("rpack file not selected.")
open_file_exist(rpack)
    
file_content = read_binary_file(rpack)
header, sections, fileparts, filemaps, fname_idxs, filename_offset = parse_binary_file(file_content)
# print(f"header: {header}")
# print(f"sections: {sections}")
# print(f"filename offset: {filename_offset}")
rpack_name = os.path.basename(rpack)
rpack_name_no_ext = os.path.splitext(rpack_name)[0]
rpack_path = os.path.dirname(rpack)    

print('######FNAME_INDICES######')
for idx, fname_idx in enumerate(fname_idxs):
    print(f"{idx} : {fname_idx}") 

def get_resource_name(file_index, fname_idxs, file_content, filename_offset):
    offset = fname_idxs[file_index][0] + filename_offset  # assuming fname_idxs[file_index] is a tuple containing offset
    filename = file_content[offset:].split(b'\x00')[0]  # Read until null byte
    return filename.decode('utf-8')  # Convert bytes to string


def get_resource_save_path(resource_name, part, is_texture):
    #rather than play with global scope variables, we'll substitute a string as a placeholder
    save_path = os.path.join("X:/SteamLibrary/steamapps/common/Dying Light 2/ph/work/data_platform/pc/assets/city", resource_name)

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if is_texture:
        save_path = os.path.join(save_path, resource_name)
    else:
        save_path = os.path.join(save_path, f"{part}_{resource_name}")

    return save_path
print(sections[0])

print('#####header#####')
print(f"Sig:        {header[0]}")
print(f"ver:        {header[1]}")
print(f"c1:         {header[2]}")
print(f"c2:         {header[3]}")
print(f"c3:         {header[4]}")
print(f"c4:         {header[5]}")
print(f"parts:      {header[6]}")
print(f"sections:   {header[7]}")
print(f"files:      {header[8]}")
print(f"fnamessize: {header[9]}")
print(f"fnames:     {header[10]}")
print(f"alignment:  {header[11]}")

print('#####sections#####')
print(f"filetype:      {sections[0][0]}")
print(f"type2:         {sections[0][1]}")
print(f"type3:         {sections[0][2]}")
print(f"type4:         {sections[0][3]}")
print(f"offset:        {sections[0][4]}")
print(f"unpackedsize:  {sections[0][5]}")
print(f"packedsize:    {sections[0][6]}")
print(f"resoucecount:  {sections[0][7]}")
print(f"unk:           {sections[0][8]}")

is_texture = False
header_size = header_type = width = height = format = mip_count = depth = tex_type = 0

# pprint(sections)
for i in range(header[8]):  # header.files
    for j in range(filemaps[i][0]):  # filemaps[i].parts_count
        open_file_exist(rpack)
        # File Size
        file_size = fileparts[filemaps[i][5] + j][4]  # fileparts[filemaps[i].first_part + j].size
        # print(header)
        print(f"sections length: {len(sections)}")
        print(f"fileparts length: {len(fileparts)}")
        print(f"fnames_idx length: {len(fname_idxs)}")
        print(f"filemaps length: {len(filemaps)}")
        print(f"i: {i}, j: {j}, filemaps[i][5] + j: {filemaps[i][5] + j}, fileparts[filemaps[i][5] + j][0]: {fileparts[filemaps[i][5] + j][0]}")

        # File Offset
        file_offset = fileparts[filemaps[i][5] + j][3]  # fileparts[filemaps[i].first_part + j].offset
        file_offset = file_offset << 4
        file_offset = file_offset + (sections[fileparts[filemaps[i][5] + j][0]][4] << 4)  # sections[fileparts[filemaps[i].first_part + j].section_index].offset
        # Detect if compressed
        assert sections[fileparts[filemaps[i][5] + j][0]][6] == 0, "Cannot extract compressed files, extraction aborted"  # sections[fileparts[filemaps[i].first_part + j].section_index].packed_size
        # Extract
        is_texture = filemaps[i][2] == 32  # filemaps[i].filetype
        
        #resource_name = get_resource_name(i, fname_idxs, file_content, header.fname_idx_offset)
        resource_name = get_resource_name(i, fname_idxs, file_content, filename_offset)

        savepath = get_resource_save_path(resource_name, j, is_texture)
        # read the width&height in the header to determine the header type
        # print(f"{resource_name}\n")
        if is_texture:
            if j == 0:
                fm.select_file(rpack)
                open_file_exist(savepath + ".header")
                fm.save_file_range(savepath + ".header", file_offset, file_size)
                fm.select_file(rpack)  # Replace rpack with the actual file path if it's not the correct variable
                header_size = fm.read_uint(file_offset + 8)
                header_type = fm.read_uint(file_offset + 64)
                width = fm.read_ushort(file_offset + 64)
                height = fm.read_ushort(file_offset + 66)
                format = fm.read_ubyte(file_offset + 70)
                depth = fm.read_ubyte(file_offset + 68)
                mip_count = fm.read_ubyte(file_offset + 71) >> 2
                tex_type = fm.read_ubyte(file_offset + 71) & 0x03  # 0 = 2d, 1 = cubemap, 2 = 3d
            else:
                if header_type != 0:
                    # fm.save_file_range(savepath + ".dds", file_offset, file_size, rpack)
                    # fm.select_file(rpack)
                    #!
                    open_file_exist(savepath + ".dds")                   
                    fm.save_file_range(savepath + ".dds", file_offset, file_size)

                    
                    dds_generate(width, height, mip_count, format, tex_type, depth, savepath + ".dds")
                    fm.save_file(savepath + ".dds")
                    fm.close_file(savepath + ".dds")
        else:
            open_file_exist(savepath) 
            fm.select_file(rpack)
            fm.save_file_range(savepath, file_offset, file_size)
            
        if fm.find_open_file(Path(rpack_path) / rpack_name):
            fm.select_file(Path(rpack_path) / rpack_name)

