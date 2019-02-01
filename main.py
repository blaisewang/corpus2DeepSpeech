"""
USE: python <FILEPATH> (options)
OPTIONS:
    -h : print this help message and exit
    -s : scp filepath
    -t : text filepath
    -o : output file prefix
"""

import getopt
import os
import re
import subprocess
import sys

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

output_directory = os.getcwd() + "/" + opts['-o']

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

file_size_list = []

with open(opts['-s']) as scp_file:
    for index, line in enumerate(scp_file):
        scp = line.split()
        output_file = output_directory + "/{0:06d}".format(index) + ".wav"
        subprocess.run([scp[1], scp[2], scp[3], scp[4], output_file])
        file_size_list.append(os.path.getsize(output_file))

train_file_count = int(0.8 * len(file_size_list))

head = "wav_filename,wav_filesize,transcript\n"
punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""

train_csv = open(opts['-o'] + "-train.csv", "w+")
dev_csv = open(opts['-o'] + "-dev.csv", "w+")

train_csv.write(head)
dev_csv.write(head)

brackets = re.compile(r'<.+>')
punctuation = re.compile('[%s]' % re.escape(punctuations))

with open(opts['-t']) as text_file:
    for index, line in enumerate(text_file):

        if file_size_list[index] < 100000:
            continue

        text = line[8:].lower()

        text = text.replace("-DASH", "")
        text = text.replace(",COMMA", "")
        text = text.replace(":COLON", "")
        text = text.replace("-HYPHEN", "")
        text = text.replace(".PERIOD", "")
        text = text.replace(";SEMI-COLON", "")
        text = text.replace("(PAREN", "")
        text = text.replace(")CLOSE_PAREN", "")
        text = text.replace("(LEFT-PAREN", "")
        text = text.replace(")RIGHT-PAREN", "")
        text = text.replace("{LEFT-BRACE", "")
        text = text.replace("}RIGHT-BRACE", "")
        text = text.replace("\'SINGLE-QUOTE", "")
        text = text.replace("\"DOUBLE-QUOTE", "")
        text = text.replace("?QUESTION-MARK", "")
        text = text.replace("!EXCLAMATION-POINT", "")

        text = text.replace("&AMPERSAND", "and")

        text = brackets.sub('', text)
        text = punctuation.sub('', text)
        text = text.replace("  ", " ")
        text = text.strip()

        wav_file = output_directory + "/{0:06d}".format(index) + ".wav"
        text = wav_file + "," + str(index) + "," + text + "\n"
        if index < train_file_count:
            train_csv.write(text)
        else:
            dev_csv.write(text)

train_csv.close()
dev_csv.close()
