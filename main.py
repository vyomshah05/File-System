from shell import Shell

if __name__ == "__main__":
    B = 64
    d = 16
    N = 4

    shell = Shell(B=B, d=d, N=N)
    shell.run()