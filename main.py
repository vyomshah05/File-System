from shell import Shell

if __name__ == "__main__":
    B = 64
    d = 16
    N = 4

    shell = Shell(B=B, d=d, N=N)
    input_file = "FS-input-1.txt"

    with open(input_file, "r") as f:
        lines = f.readlines()
    shell.run(lines)