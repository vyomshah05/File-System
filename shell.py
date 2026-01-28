from file_system import FS

class Shell:
    def __init__(self, B, d, N):
        self.fs = FS(B=B, d=d, N=N)

    def run(self):
        while True:
            try:
                line = input("$ ").strip()
            except EOFError:
                break
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            try:
                if cmd == "q":
                    break

                elif cmd == "in":
                    self.fs.init()
                    print("system initialized")

                elif cmd == "cr":
                    self.fs.create(parts[1])
                    print(parts[1], "created")

                elif cmd == "de":
                    self.fs.destroy(parts[1])
                    print(parts[1], "destroyed")
                
                elif cmd == "op":
                    h = self.fs.open(parts[1])
                    print(parts[1], 'opened', h)

                elif cmd == "cl":
                    self.fs.close(int(parts[1]))
                    print(parts[1], "closed")

                elif cmd == "rd":
                    h = int(parts[1]); m = int(parts[2]); n = int(parts[3])
                    r = self.fs.read(h, m, n)
                    print(r, "bytes read from file", h)

                elif cmd == "wr":
                    h = int(parts[1]); m = int(parts[2]); n = int(parts[3])
                    w = self.fs.write(h, m, n)
                    print(w, "bytes written to file", h)

                elif cmd == "sk":
                    h = int(parts[1]); pos = int(parts[2])
                    self.fs.seek(h, pos)
                    print("position is", pos)

                elif cmd == "dr":
                    for name, size in self.fs.directory():
                        print(name, size, end = ' ')
                    print()
                    

                elif cmd == "wm":
                    m = int(parts[1])
                    s = line.split(None, 2)[2]
                    s = s.strip()
                    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
                        s = s[1:-1]
                    n = self.fs.write_memory(m, s)
                    print(n, "bytes written to M")

                elif cmd == "rm":
                    m = int(parts[1]); n = int(parts[2])
                    print(self.fs.read_memory(m, n).decode('ASCII'))

                elif cmd == "sv":
                    self.fs.save(parts[1])
                    print("saved")

                elif cmd == "rs":
                    self.fs.restore(parts[1])
                    print("restored")

                else:
                    print("unknown command")
            except Exception as e:
                print("error")
                #raise e