"""
USE: python <FILEPATH> (options)
OPTIONS:
    -h : print this help message and exit
    -t : train set directory
    -e : test set directory
    -d : dev set directory
"""

import getopt
import multiprocessing
import os
import re
import subprocess
import sys

opts, args = getopt.getopt(sys.argv[1:], 'ht:e:d:')
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

if '-t' not in opts:
    print("\n** ERROR: must specify train set directory (opt: -s) **\n", file=sys.stderr)
    print_help()

if '-e' not in opts:
    print("\n** ERROR: must specify test set directory (opt: -t) **\n", file=sys.stderr)
    print_help()

if '-d' not in opts:
    print("\n** ERROR: must specify dev set directory (opt: -t) **\n", file=sys.stderr)
    print_help()

current_directory = os.getcwd()

output_directories = [current_directory + "/wsj-train",
                      current_directory + "/wsj-test",
                      current_directory + "/wsj-dev"]

brackets = re.compile(r'<.+>')
head = "wav_filename,wav_filesize,transcript\n"
punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""
punctuation = re.compile('[%s]' % re.escape(punctuations))


def mkdir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


for directory in output_directories:
    mkdir(directory)


def scp_file_read(arg):
    path, output = arg

    sox_args_list = []
    with open(path + "/wav.scp") as scp_file:
        for index, line in enumerate(scp_file):
            scp_array = line.split()
            output_file = output + "/{0:06d}".format(index) + ".wav"
            sox_args_list.append([scp_array[1], scp_array[2], scp_array[3], scp_array[4], output_file])

    return sox_args_list


def convert(arg):
    subprocess.run(arg)


def text_read(arg):
    data_directory, wav_directory = arg

    csv_args_list = []
    with open(data_directory + "/text") as text_file:
        for index, line in enumerate(text_file):
            csv_args_list.append((line, index, wav_directory))

    return csv_args_list


def format_csv(arg):
    text, index, wav_directory = arg

    text = text[8:]

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

    text = text.lower()

    text = brackets.sub('', text)
    text = punctuation.sub('', text)
    text = text.replace("  ", " ")
    text = text.strip()

    wav_file = wav_directory + "/{0:06d}".format(index) + ".wav"
    frames = int(subprocess.check_output(['soxi', '-s', wav_file], stderr=subprocess.STDOUT))

    if len(text) < 4:
        return
    if frames / 16000 > 10:
        return
    if int(frames / 16000 * 1000 / 10 / 2) < len(text):
        return

    return wav_file + "," + str(os.path.getsize(wav_file)) + "," + text + "\n"


args_list = [(opts['-t'], output_directories[0]),
             (opts['-e'], output_directories[1]),
             (opts['-d'], output_directories[2])]

pool = multiprocessing.Pool()

print("\nStart analysing SCP files ...")

scp_results = pool.map(scp_file_read, args_list)

print("Done\n")

async_results = []

print("Start converting wav files to current directory ...")

for result in scp_results:
    async_results.append(pool.map_async(convert, result))

for index, async_result in enumerate(async_results):
    async_result.wait()
    print("Done for", index)

print("\nStart analysing TEXT files ...")

read_results = pool.map(text_read, args_list)

print("Done\n")

train_csv = open("wsj-train.csv", "w+")
test_csv = open("wsj-test.csv", "w+")
dev_csv = open("wsj-dev.csv", "w+")

csv_list = [train_csv, test_csv, dev_csv]

for i, csv_file in enumerate(csv_list):

    print("Start writing text to", csv_file.name, "...")

    csv_file.write(head)

    print("Start formatting CSV result ...")
    format_results = pool.map(format_csv, read_results[i])

    for result in format_results:
        if result is not None:
            csv_file.write(result)

    csv_file.close()

    print("Done\n")
