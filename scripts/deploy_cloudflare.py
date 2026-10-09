"""Run Wrangler and publish a redacted failure annotation for remote diagnosis."""
import os
import re
import subprocess
import sys


def failure_summary(output):
    output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", output)
    for name, value in os.environ.items():
        if value and any(word in name.upper() for word in ("TOKEN", "SECRET", "API_KEY", "DATABASE_URL")):
            output = output.replace(value, "[redacted]")
    output = re.sub(r"postgres(?:ql)?://\S+", "[redacted database URL]", output)
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if "[ERROR]" in line or "ERROR:" in line or line.lstrip().startswith("ERROR "):
            return " | ".join(lines[index:index + 12])[:1500]
    return "Wrangler deployment failed; open the deployment step logs for details."


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "deploy"
    process = subprocess.Popen(["npm", "run", command], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True)
    lines = []
    for line in process.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    code = process.wait()
    if code:
        message = failure_summary("".join(lines))
        # Escape GitHub workflow command data, preserving a single annotation.
        message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error::{message}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
