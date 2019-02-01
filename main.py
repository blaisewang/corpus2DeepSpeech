"""
USE: python <FILEPATH> (options)
OPTIONS:
    -h : print this help message and exit
    -s : scp filepath
    -t : text filepath
    -o : output file prefix
"""
################################################################

import getopt
import sys

################################################################
# Command line options handling, and help

opts, args = getopt.getopt(sys.argv[1:], 'hs:t:o:')
opts = dict(opts)


def print_help():
    help_info = __doc__.replace('<FILEPATH>', sys.argv[0], 1)
    print('-' * 60, help_info, '-' * 60, file=sys.stderr)
    sys.exit()


if '-h' in opts:
    print_help()

if len(args) > 0:
    print("\n** ERROR: no arg files - only options! **\n", file=sys.stderr)
    print_help()

if '-s' not in opts:
    print("\n** ERROR: must specify scp filepath (opt: -s) **\n", file=sys.stderr)
    print_help()

if '-t' not in opts:
    print("\n** ERROR: must specify text filepath (opt: -t) **\n", file=sys.stderr)
    print_help()

if '-o' not in opts:
    print("\n** ERROR: must specify output file prefix (opt: -o) **\n", file=sys.stderr)
    print_help()

with open(opts['-s']) as scp_file:
    for line in scp_file:
        print(line.split())
        break
