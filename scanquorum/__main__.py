import sys

USAGE = """scanquorum <command> [options]

  build <pdf>        read a PDF with every installed engine, write .md + unconfirmed index
  verify-ai          ask a vision model about the unconfirmed places (it may only CHOOSE)
  version

Docs: README.md   What it cannot do: artifacts/ARTIFACTS.md
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "build":
        from .build import main as m
        return m(rest)
    if cmd in ("verify-ai", "verify_ai"):
        from .verify_ai import main as m
        return m(rest)
    if cmd == "version":
        from . import __version__
        print("scanquorum " + __version__)
        return 0
    print("unknown command %r\n" % cmd)
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
