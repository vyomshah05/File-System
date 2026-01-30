from file_system import FS

class Shell:
    def __init__(self, B, d, N):
        self.fs = FS(B=B, d=d, N=N)

    def run(self, lines, output_file="output.txt"):
        out_lines = []
        def emit(s=""):
            out_lines.append(s)
        i = 1
        for line in lines:
            if not line.strip():
                emit('\n')
                continue
            parts = line.split()
            cmd = parts[0].lower()
            if cmd == 'in':
                #print("\n\nRun", i)
                i += 1
            #print(parts, end=' ')
            #print(line)
            try:
                if cmd == "q":
                    break

                elif cmd == "in":
                    self.fs.init()
                    emit("system initialized")

                elif cmd == "cr":
                    self.fs.create(parts[1])
                    emit(f"{parts[1]} created")

                elif cmd == "de":
                    self.fs.destroy(parts[1])
                    emit(f"{parts[1]} destroyed")
                
                elif cmd == "op":
                    h = self.fs.open(parts[1])
                    emit(f"{parts[1]} opened {h}")

                elif cmd == "cl":
                    self.fs.close(int(parts[1]))
                    emit(f"{parts[1]} closed")

                elif cmd == "rd":
                    h = int(parts[1]); m = int(parts[2]); n = int(parts[3])
                    r = self.fs.read(h, m, n)
                    emit(f"{r} bytes read from file {h}")

                elif cmd == "wr":
                    h = int(parts[1]); m = int(parts[2]); n = int(parts[3])
                    w = self.fs.write(h, m, n)
                    emit(f"{w} bytes written to file {h}")

                elif cmd == "sk":
                    h = int(parts[1]); pos = int(parts[2])
                    self.fs.seek(h, pos)
                    emit(f"position is {pos}")

                elif cmd == "dr":
                    res = ""
                    for name, size in self.fs.directory():
                        res += f"{name} {size} "
                    emit(res.strip())
                    

                elif cmd == "wm":
                    m = int(parts[1])
                    s = line.split(None, 2)[2]
                    s = s.strip()
                    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
                        s = s[1:-1]
                    n = self.fs.write_memory(m, s)
                    emit(f"{n} bytes written to M")

                elif cmd == "rm":
                    m = int(parts[1]); n = int(parts[2])
                    emit(self.fs.read_memory(m, n).decode('ASCII'))

                elif cmd == "sv":
                    self.fs.save(parts[1])
                    emit("saved")

                elif cmd == "rs":
                    self.fs.restore(parts[1])
                    emit("restored")

                else:
                    emit("unknown command")
            except Exception as e:
                emit("error")
                #print(e)
                #raise e
            with open(output_file, "w") as f:
                res = ""
                for line in out_lines:
                    res += line + "\n"
                f.write(res)