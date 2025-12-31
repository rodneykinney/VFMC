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
            sol = DrSolution.parse(alg)
            skeleton = sol.reduce()
            if skeleton.alg not in skels:
                skels.add(skeleton.alg)
                sol_length = sum(1 for _ in alg.split(" "))
                skel_length = sum(1 for _ in skeleton.alg.split(" "))
                max_delta = max(len(so.moves) - len(sk.moves) for so,sk in zip(sol.parts, skeleton.parts))
                print(f"{skeleton.alg}{' (p)' if False else ''} : {alg}\t{skel_length}\t{sol_length}\t{sol_length - skel_length}\t{max_delta}")




