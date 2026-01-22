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
                'dirty': False
            })

    def init(self):
        self.disk = EmulatedDisk(self.b)
        self.format_fs()

        self.I = bytearray(BLOCK_SIZE)
        self.O = bytearray(BLOCK_SIZE)
        self.M = bytearray(BLOCK_SIZE)

        self.OFT = []
        for _ in range(self.N):
            self.OFT.append({
                'desc': -1,
                'pos': -1,
                'len': 0,
                'buf': bytearray(BLOCK_SIZE),
                'buf_i': -1,
                'dirty': False
            })

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
        desc = {
            'length': self._get_int(self.I, offset),
            'ptrs': [self._get_int(self.I, offset + 4 + j * INT_SIZE) for j in range(POINTERS)]
        }
        return desc
