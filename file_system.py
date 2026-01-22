import struct

INT_FMT = '<i'
INT_SIZE = 4
BLOCK_SIZE = 512
DESCRIPTOR_FIELDS = 4
DESCRIPTOR_SIZE = 16
DESCRIPTOR_PER_BLOCK = 32
POINTERS = 3

class EmulatedDisk:
    def __init__(self, B: int):
        self.B = B
        self.D = [bytearray(BLOCK_SIZE) for i in range(B)]

    def read_block(self, b: int, I: bytearray):
        if 0 <= b < self.B:
            I[:] = bytes(self.D[b])
        else:
            print('Block out of bounds')
        
    def write_block(self, b: int, O: bytearray):
        if 0 <= b < self.B:
            self.D[b][:] = O
        else:
            print('Block out of bounds')

class FS:
    def __init__(self, B: int = 64, d: int = 192, N: int = 4):
        self.block_size = BLOCK_SIZE
        self.b = B
        self.N = N

        self.k = (self.d + DESCRIPTOR_PER_BLOCK - 1) // DESCRIPTOR_PER_BLOCK + 1

        self.disk = EmulatedDisk(B)
        self.format_fs()

        self.I = bytearray(BLOCK_SIZE)
        self.O = bytearray(BLOCK_SIZE)
        self.M = bytearray(BLOCK_SIZE)

        self.OFT = []
        for _ in range(N):
            self.OFT.append({
                'desc': -1,
                'pos': -1,
                'len': 0,
                'buf': bytearray(BLOCK_SIZE),
                'buf_i': -1,
                'not_flushed': False
            })
        
        self.init()
    
    #--- File System Methods ---#

    def init(self):
        '''Re-initialize the file system'''
        self.disk = EmulatedDisk(self.b)
        self.format_fs()

        #Reset buffers
        self.I[:] = b'\x00' * BLOCK_SIZE
        self.O[:] = b'\x00' * BLOCK_SIZE
        self.M[:] = b'\x00' * BLOCK_SIZE

        #Reset OFT
        self.OFT = []
        for i in range(self.N):
            self.OFT[i]['buf'][:] = b'\x00' * BLOCK_SIZE
            self.OFT[i]['pos'] = -1
            self.OFT[i]['len'] = 0
            self.OFT[i]['buf_i'] = -1
            self.OFT[i]['not_flushed'] = False
            self.OFT[i]['desc'] = -1

        #Reset bitmap
        for b in range(0, self.k + 1):
            self._bitmap_set(b, 1)
        for b in range(self.k + 1, self.B):
            self._bitmap_set(b, 0)

        #Initialize descriptors
        for i in range(self.d):
            self._write_desc(i, -1, -1, -1, -1)

        #Set directory descriptor
        self._write_desc(0, 0, self.k, -1, -1)

        #Zero directory block
        self.O[:] = b'\x00' * BLOCK_SIZE
        self.disk.write_block(self.k, self.O)

        #Open directory in OFT[0]
        self.OFT[0]['desc'] = 0
        self.OFT[0]['pos'] = 0
        self.OFT[0]['len'] = 0
        self.OFT[0]['buf_i'] = 0
        self.OFT[0]['not_flushed'] = False

        #Load directory block into OFT[0] buffer
        self.disk.read_block(self.k, self.OFT[0]['buf'])
        self.OFT[0]['buf'][:] = self.I[:]

    def format_fs(self):
        '''Format the file system'''
        #Initialize all blocks to zero
        zero_block = bytearray(BLOCK_SIZE)
        for b in range(self.b):
            self.disk.write_block(b, zero_block)

    def create(self, name: str):
        '''Create a new file with the given name'''
        if self._dir_find(name) != -1:
            raise ValueError("File already exists")
        if len(name) > 4:
            raise ValueError("Filename too long")

        #Check if file already exists
        free = -1
        for j in range(1, self.d):
            sz, _, _, _ = self._read_desc(j)
            if sz == -1:
                free = j
                break
        if free == -1:
            raise RuntimeError("no free descriptor")
        
        self._write_desc(free, 0, -1, -1, -1)
        self._dir_add(name, free)

    def destroy(self, name: str):
        di = self._dir_find(name)
        if di == -1:
            raise ValueError("File not found")
        
        for i in range(1, self.N):
            if self.OFT[i]['pos'] != -1 and self.OFT[i]['desc'] == di:
                raise RuntimeError("file is open")
        
        size, b0, b1, b2 = self._read_desc(di)
        for b in [b0, b1, b2]:
            if b != -1:
                self._free_block(b)

        self._write_desc(di, -1, -1, -1, -1)
        self._dir_remove(name)

    def open(self, name: str) -> int:
        di = self._dir_find(name)
        if di == -1:
            raise ValueError("File not found")
        
        for i in range(1, self.N):
            if self.OFT[i]['pos'] != -1 and self.OFT[i]['desc'] == di:
                return i
        
        for i in range(1, self.N):
            if self.OFT[i]['pos'] == -1:
                self.OFT[i]['desc'] = di
                self.OFT[i]['pos'] = 0
                size, b0, b1, b2 = self._read_desc(di)
                self.OFT[i]['len'] = size
                self.OFT[i]['buf_i'] = 0
                self.OFT[i]['not_flushed'] = False

                block_num = b0 if b0 != -1 else -1
                if block_num != -1:
                    self.disk.read_block(block_num, self.OFT[i]['buf'])
                else:
                    self.OFT[i]['buf'][:] = b'\x00' * BLOCK_SIZE

                return i
        
        raise RuntimeError("no free OFT entry")
    
    def close(self, i: int):
        '''Close the file associated with the given OFT index'''
        if i < 0 or i >= self.N:
            raise IndexError("OFT index out of bounds")
        if self.OFT[i]['pos'] == -1:
            raise RuntimeError("OFT entry not in use")
        
        self._flush_oft(i)
        self.OFT[i]['desc'] = -1
        self.OFT[i]['pos'] = -1
        self.OFT[i]['len'] = 0
        self.OFT[i]['buf_i'] = -1
        self.OFT[i]['not_flushed'] = False
        self.OFT[i]['cur'] = -1

    def read(self, i: int, m: int, n: int) -> bytes:
        '''Read n bytes from the file associated with the given OFT index'''
        if i < 0 or i >= self.N:
            raise IndexError("OFT index out of bounds")
        if self.OFT[i]['pos'] == -1:
            raise RuntimeError("OFT entry not in use")
        
        di = self.OFT[i]['desc']
        off = self.OFT[i]['pos']
        size = self.OFT[i]['len']
        if off >= size:
            return 0
        
        m = min(n, size - off)
        read_count = 0

        while n > 0:
            block_index = off // BLOCK_SIZE
            block_offset = off % BLOCK_SIZE

            if self.OFT[i]['buf_i'] != block_index:
                self._load_oft_block(i, block_index)

            to_read = min(n, BLOCK_SIZE - block_offset)
            self.M[m:m+to_read] = self.OFT[i]['buf'][block_offset:block_offset + to_read]

            m += to_read
            off += to_read
            n -= to_read
            read_count += to_read

        self.OFT[i]['pos'] += off
        return read_count
    
    def write(self, i: int, m: int, n: int):
        '''Write n bytes to the file associated with the given OFT index'''
        if i < 0 or i >= self.N:
            raise IndexError("OFT index out of bounds")
        if self.OFT[i]['pos'] == -1:
            raise RuntimeError("OFT entry not in use")
        
        di = self.OFT[i]['desc']
        off = self.OFT[i]['pos']
        written_count = 0

        while n > 0:
            block_index = off // BLOCK_SIZE
            block_offset = off % BLOCK_SIZE

            if block_index >= 3:
                raise RuntimeError("File size limit exceeded")

            if self.OFT[i]['buf_i'] != block_index:
                self._load_oft_block(i, block_index)

            size, ptrs = self._get_block_ptr(di)
            if ptrs[block_index] == -1:
                ptrs[block_index] = self._alloc_block()
                self._write_desc(di, size, ptrs[0], ptrs[1], ptrs[2])

            to_write = min(n, BLOCK_SIZE - block_offset)
            self.OFT[i]['buf'][block_offset:block_offset + to_write] = self.M[m:m + to_write]
            self.OFT[i]['not_flushed'] = True

            m += to_write
            off += to_write
            n -= to_write
            written_count += to_write
            self.OFT[i]['len'] = max(self.OFT[i]['len'], self.OFT[i]['pos'])

        self.OFT[i]['pos'] += off
        return written_count
    
    def seek(self, i: int, pos: int):
        '''Seek to a position in the file associated with the given OFT index'''
        if i < 0 or i >= self.N:
            raise IndexError("OFT index out of bounds")
        if self.OFT[i]['pos'] == -1:
            raise RuntimeError("OFT entry not in use")
        if pos < 0 or pos > self.OFT[i]['len']:
            raise ValueError("Seek position out of bounds")
        
        old_index = self.OFT[i]['pos'] // BLOCK_SIZE
        block_index = pos // BLOCK_SIZE
        if block_index != old_index:
            self._load_oft_block(i, block_index)
        
        self.OFT[i]['pos'] = pos
    
    def directory(self) -> list[tuple[str, int]]:
        '''List the contents of the directory'''
        entries = []
        n = self._dir_entry_count()
        for i in range(n):
            name, di = self._dir_read_entry(i)
            if name != '':
                entries.append((name, di))
        return entries

    #--- Helper Methods ---#

    #Int helper methods

    def _get_int(self, byte_array: bytearray, index: int) -> int:
        '''Read 4 byte ints from byte array'''
        return struct.unpack_from(INT_FMT, byte_array, index)[0]
    
    def _set_int(self, byte_array: bytearray, index: int, value: int):
        '''Write ints into byte array'''
        struct.pack_into(INT_FMT, byte_array, index, value)

    #Bitmap helper methods

    def _bitmap_get(self, i: int) -> bool:
        '''Get the i-th bit from the bitmap'''
        self.disk.read_block(0, self.I)
        byte = self.I[i // 8]
        return (byte & (1 << (i % 8))) != 0
    
    def _bitmap_set(self, i: int, val: bool):
        '''Set the i-th bit in the bitmap'''
        self.disk.read_block(0, self.I)
        byte = self.I[i // 8]
        if val:
            byte |= (1 << (i % 8))
        else:
            byte &= ~(1 << (i % 8))
        self.I[i // 8] = byte
        self.disk.write_block(0, self.I)

    def _alloc_block(self) -> int:
        '''Allocate a free block from the bitmap'''
        for b in range(self.k + 1, self.B):
            if self._bitmap_get(b) == 0:
                self._bitmap_set(b, 1)
                self.O[:] = b'\x00' * BLOCK_SIZE
                self.disk.write_block(b, self.O)
                return b
        raise RuntimeError("disk full")
    
    def _free_block(self, b: int):
        '''Free a block in the bitmap'''
        self._bitmap_set(b, 0)

    #Descriptor helper methods

    def _desc_loc(self, i: int) -> tuple[int, int]:
        '''Get the block and offset for a descriptor index'''
        block = 1 + i // DESCRIPTOR_PER_BLOCK
        offset = (i % DESCRIPTOR_PER_BLOCK) * DESCRIPTOR_SIZE
        return block, offset
    
    def _read_desc(self, i: int) -> tuple[int, int, int, int]:
        '''Read a descriptor from disk'''
        block, offset = self._desc_loc(i)
        self.disk.read_block(block, self.I)
        size = self._get_int(self.I, offset + 0)
        b0 = self._get_int(self.I, offset + 4)
        b1 = self._get_int(self.I, offset + 8)
        b2 = self._get_int(self.I, offset + 12)
        return size, b0, b1, b2

    def _write_desc(self, i: int, size: int, b0: int, b1: int, b2: int):
        '''Write a descriptor to disk'''
        block, offset = self._desc_loc(i)
        self.disk.read_block(block, self.I)
        self.O[:] = self.I[:]
        self._set_int(self.O, offset + 0, size)
        self._set_int(self.O, offset + 4, b0)
        self._set_int(self.O, offset + 8, b1)
        self._set_int(self.O, offset + 12, b2)
        self.disk.write_block(block, self.O)

    # File name helper methods

    def _pack_name(self, name: str) -> bytearray:
        '''Pack a filename into a 16-byte bytearray'''
        name_bytes = name.encode('ascii')
        if len(name_bytes) > 4:
            raise ValueError("Filename too long")
        return name_bytes.ljust(4, b'\x00')
    
    def _unpack_name(self, name_bytes: bytearray) -> str:
        '''Unpack a filename from a 16-byte bytearray'''
        return name_bytes.split(b'\x00', 1)[0].decode('ascii')
    
    # Directory entry helper methods

    def _dir_entry_count(self) -> int:
        '''Count the number of directory entries in a directory OFT entry'''
        size, _, _, _ = self._read_desc(0)
        return size // 8
    
    def _dir_read_entry(self, i: int) -> tuple[str, int]:
        '''Read a directory entry by index'''
        if i < 0 or i >= self._dir_entry_count():
            raise IndexError("Directory entry index out of bounds")

        off = i * 8
        name = self._unpack_name(self._read_file_by_desc(0, off, 8)[0:4])
        di = struct.unpack(INT_FMT, self._read_file_by_desc(0, off, 8))[0]
        return name, di
    
    def _dir_write_entry(self, i: int, name: bytes, di: int):
        '''Write a directory entry by index'''
        off = i * 8
        data = name + struct.pack(INT_FMT, di)
        self._write_file_by_desc(0, off, data)

    def _dir_find(self, name: str) -> int:
        n = self._dir_entry_count()
        for i in range(n):
            nm, di = self._dir_read_entry(i)
            if nm == name:
                return di
        return -1

    def _dir_add(self, name: str, di: int):
        '''Add a directory entry'''
        packed_name = self._pack_name(name)
        n = self._dir_entry_count()
        
        for i in range(n):
            entry_name, _ = self._dir_read_entry(i)
            if entry_name == name:
                raise ValueError("File already exists")
            elif entry_name == '':
                self._dir_write_entry(i, packed_name, di)
                return
        self._dir_write_entry(n, packed_name, di)

    def _dir_remove(self, name: str):
        '''Remove a directory entry'''
        n = self._dir_entry_count()
        for i in range(n):
            entry_name, _ = self._dir_read_entry(i)
            if entry_name == name:
                self._dir_write_entry(i, b'\x00' * 4, -1)
                return
        raise ValueError("File not found")

    # File read/write helper methods

    def _get_block_ptr(self, desc: int) -> tuple[int, list[int]]:
        '''Get the block pointers from a descriptor'''
        size, b0, b1, b2 = self._read_desc(desc)
        return size, [b0, b1, b2]
    
    def _read_file_from_desc(self, desc: int, off: int, n: int) -> bytes:
        '''Read data from a file given its descriptor index'''
        size, blocks = self._get_block_ptr(desc)
        if off >= size:
            return b''
        n = min(n, size - off)

        out = bytearray()
        while n > 0:
            block_index = off // BLOCK_SIZE
            block_offset = off % BLOCK_SIZE
            block_num = blocks[block_index] if block_index < POINTERS else -1

            if block_index >= 3:
                break
            if block_num == -1:
                break

            self.disk.read_block(block_num, self.I)
            to_read = min(n, BLOCK_SIZE - block_offset)
            out += self.I[block_offset:block_offset + to_read]

            off += to_read
            n -= to_read
        
        return bytes(out)
    
    def _write_file_by_desc(self, desc: int, off: int, data: bytes):
        '''Write data to a file given its descriptor index'''
        size, blocks = self._get_block_ptr(desc)
        n = len(data)
        data_offset = 0

        while n > 0:
            block_index = off // BLOCK_SIZE
            block_offset = off % BLOCK_SIZE

            if block_index >= 3:
                raise RuntimeError("File size limit exceeded")

            if blocks[block_index] == -1:
                blocks[block_index] = self._alloc_block()
                self._write_desc(desc, size, *blocks)

            block_num = blocks[block_index]
            self.disk.read_block(block_num, self.I)
            self.O[:] = self.I[:]

            to_write = min(n, BLOCK_SIZE - block_offset)
            self.O[block_offset:block_offset + to_write] = data[data_offset:data_offset + to_write]
            self.disk.write_block(block_num, self.O)

            off += to_write
            data_offset += to_write
            n -= to_write
            size = max(size, off)

        self._write_desc(desc, size, blocks[0], blocks[1], blocks[2])

    #OFT helper methods

    def _flush_oft(self, i: int):
        '''Flush the buffer of an OFT entry to disk'''
        if not self.OFT[i]['not_flushed']:
            return
        di = self.OFT[i]['desc']
        _, ptrs = self._get_block_ptrs(di)
        lbi = self.OFT[i]['cur']
        if lbi == -1:
            self.OFT[i]['dirty'] = False
            return

        disk_block = ptrs[lbi]
        if disk_block == -1:
            disk_block = self._alloc_block()
            ptrs[lbi] = disk_block
            size, _ = self._get_block_ptrs(di)
            self._write_desc(di, size, ptrs[0], ptrs[1], ptrs[2])

        self.O[:] = self.OFT[i]['buf'][:]
        self.disk.write_block(disk_block, self.O)
        self.OFT[i]['dirty'] = False

    def _load_oft_block(self, i: int, block_index: int):
        '''Load a block into the OFT entry buffer'''
        self._flush_oft_entry(i)

        di = self.OFT[i]['desc']
        _, ptrs = self._get_block_ptrs(di)

        self.OFT[i]['buf'][:] = b'\x00' * BLOCK_SIZE
        self.OFT[i]['cur'] = block_index
        self.OFT[i]['dirty'] = False

        disk_block = ptrs[block_index]
        if disk_block == -1:
            self.disk.read_block(disk_block, self.OFT[i]['buf'])