import sys
import subprocess
import skeleton
from skeleton import DrSolution

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print("skeleton\tsolution\tskeleton length\tsolution length\tadditional moves\tmax additional moves")
    for _ in range(count):
        short_scramble = subprocess.check_output(["nissy","scramble","dr"]).decode("utf-8").strip()
        long_scramble = subprocess.check_output(["nissy", "solve", "drudfin", "-n", "1", "-m","18","-p", short_scramble]).decode("utf-8").strip()
        long_scramble = "U D R2 U D' B2 U' F2 L2 F2 R2 D' F2 D2 R2 F2 R2 B2"
        print(f"## {long_scramble}")
        p = subprocess.run(["nissy", "solve", "drudfin", "-p", "-M", "16", "-n", "100", long_scramble], encoding="UTF8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.stderr:
            raise Exception(p.stderr)
        output = p.stdout
        skels = set()
        for alg in p.stdout.split("\n"):
            alg = alg.strip()
            if not alg:
                continue
            sol = DrSolution(alg)
            if sol.corner_skeleton.alg not in skels:
                skels.add(sol.corner_skeleton.alg)
                print(sol)
                print(f"{sol.corner_skeleton.alg}: {sol.additions_section_moves}")
                print("--")




