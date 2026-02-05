# File System Emulator

## Overview
This project implements a simplified **file system emulator** in Python. The system simulates a disk, file descriptors, a directory, and an open file table (OFT), and supports basic file operations such as creating, deleting, opening, reading, writing, and seeking within files.

All functionality is exposed through a **shell-style command interface**, allowing the system to be tested using scripted input files.

---

## Features
- Emulated disk with fixed-size blocks
- Bitmap-based block allocation
- File descriptors with direct block pointers
- Single-level directory implemented as a file
- Open File Table (OFT) with buffering
- Memory read/write support
- Persistent disk save and restore
- Robust error handling per specification

---

## System Architecture

### Disk
- The disk is emulated as an array of fixed-size blocks (`512 bytes` each).
- Block 0 contains the bitmap.
- Blocks 1 through `k−1` contain file descriptors.
- Block `k` is the directory’s first data block.
- Remaining blocks store file data.

### File Descriptors
Each file descriptor contains:
- File size (bytes)
- Three direct block pointers  

Maximum file size is **3 × 512 = 1536 bytes**.

Descriptor 0 is reserved for the directory.

---

### Directory
- Implemented as a normal file.
- Each entry is 8 bytes:
  - 4-byte file name (max 4 characters)
  - 4-byte descriptor index
- Deleted files leave empty directory slots.

---

### Open File Table (OFT)
- Fixed number of entries (`N = 4`)
- Entry 0 is always reserved for the directory
- Each entry tracks:
  - Descriptor index
  - Current position
  - File length
  - Current block buffer
  - Dirty flag

---

### Memory
- A 512-byte memory array (`M`) is used as an I/O buffer for read and write operations.

---

## Supported Commands

| Command | Description |
|------|-----------|
| `in` | Initialize the file system |
| `cr <name>` | Create a new file |
| `de <name>` | Delete a file |
| `op <name>` | Open a file |
| `cl <index>` | Close an open file |
| `rd <index> <mem> <count>` | Read from file to memory |
| `wr <index> <mem> <count>` | Write from memory to file |
| `sk <index> <pos>` | Seek within a file |
| `dr` | List directory contents |
| `wm <mem> <string>` | Write string to memory |
| `rm <mem> <count>` | Read memory contents |
| `sv <file>` | Save disk image |
| `rs <file>` | Restore disk image |
| `q` | Quit |

If any command fails, the output is:

## Run
To run, run main.py and edit line 9 to include the wanted input file

`input_file = "FS-input-1.txt"`
