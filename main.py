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

with open(opts['-s']) as scp_file:
    for index, line in enumerate(scp_file):
        scp = line.split()
        output_file = output_directory + "/{0:06d}".format(index) + ".wav"
        subprocess.run([scp[1], scp[2], scp[3], scp[4], output_file])

head = "wav_filename,wav_filesize,transcript\n"
punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""

train_csv = open(opts['-o'] + "-train.csv", "w+")
train_csv.write(head)

brackets = re.compile(r'<.+>')
punctuation = re.compile('[%s]' % re.escape(punctuations))

with open(opts['-t']) as text_file:
    for index, line in enumerate(text_file):

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
        frames = int(subprocess.check_output(['soxi', '-s', wav_file], stderr=subprocess.STDOUT))

        if len(text) < 4:
            continue
        if frames / 16000 > 10:
            continue
        if int(frames / 16000 * 1000 / 10 / 2) < len(text):
            continue

        text = wav_file + "," + str(os.path.getsize(wav_file)) + "," + text + "\n"
        train_csv.write(text)

train_csv.close()
