"""
USE: python <FILEPATH> (options)
OPTIONS:
    -h : print this help message and exit
    -t : train set directory
    -e : test set directory
    -d : dev set directory
    -m : mode e.g. wsj, swb, ami
"""

import getopt
import multiprocessing
import os
import re
import subprocess
import sys
from enum import Enum

opts, args = getopt.getopt(sys.argv[1:], 'ht:e:d:m:')
opts = dict(opts)


class Mode(Enum):
    WSJ = "wsj"
    SWB = "swb"
    AMI = "ami"


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
    print("\n** ERROR: must specify train set directory (opt: -t) **\n", file=sys.stderr)
    print_help()

if '-e' not in opts:
    print("\n** ERROR: must specify test set directory (opt: -e) **\n", file=sys.stderr)
    print_help()

if '-d' not in opts:
    print("\n** ERROR: must specify dev set directory (opt: -d) **\n", file=sys.stderr)
    print_help()

if '-m' not in opts:
    print("\n** ERROR: must specify mode (opt: -m) **\n", file=sys.stderr)
    print_help()

if opts['-m'] == "swb":
    mode = Mode.SWB
elif opts['-m'] == "ami":
    mode = Mode.AMI
else:
    mode = Mode.WSJ

mode_value = str(mode.value)

current_directory = os.getcwd()

output_directories = [current_directory + "/" + mode_value + "-train",
                      current_directory + "/" + mode_value + "-test",
                      current_directory + "/" + mode_value + "-dev"]

if mode == Mode.SWB:
    brackets = re.compile(r'[.+]')
else:
    brackets = re.compile(r'<.+>')

head = "wav_filename,wav_filesize,transcript\n"
punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""
punctuation = re.compile('[%s]' % re.escape(punctuations))


def ns_to_ms(time_point):
    return int(time_point) / 100


def mkdir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


for directory in output_directories:
    mkdir(directory)

if mode == mode.SWB:
    mkdir(current_directory + "/wav")


def scp_file_read(arg):
    path, output = arg

    sox_args_list = []

    if mode == Mode.SWB:

        with open(path + "/wav.scp") as scp_file:
            for index, line in enumerate(scp_file):
                scp = line.split()
                output_file = "wav/" + scp[0] + ".wav"
                sox_args_list.append([scp[1], scp[2], scp[3], scp[4], scp[5], scp[6], scp[7], output_file])

    else:
        with open(path + "/wav.scp") as scp_file:
            for index, line in enumerate(scp_file):
                scp = line.split()
                output_file = output + "/{0:06d}".format(index) + ".wav"
                sox_args_list.append([scp[1], scp[2], scp[3], scp[4], output_file])

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
    line, index, output_directory = arg

    if mode == mode.SWB:
        prefix = line[0:23]
        prefix = prefix.split("_")
        time = prefix[1].split("-")

        input_file = "wav/" + prefix[0] + ".wav"
        output_file = output_directory + "/{0:06d}".format(index) + ".wav"

        length = float(subprocess.check_output(['soxi', '-D', input_file], stderr=subprocess.STDOUT))

        start_position = str(ns_to_ms(time[0]))
        end_position = ns_to_ms(time[1]) if ns_to_ms(time[1]) < length else length
        end_position = "=" + str(end_position)
        subprocess.run(["sox", input_file, "-e", "signed-integer",
                        "-r", "16000", output_file,
                        "trim", start_position, end_position])

        text = line[23:]
        text = text.replace("&", " and")

    else:
        text = line[8:]

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

        output_file = output_directory + "/{0:06d}".format(index) + ".wav"

    text = text.lower()

    text = brackets.sub('', text)
    text = punctuation.sub('', text)
    text = text.replace("  ", " ")
    text = text.strip()

    frames = int(subprocess.check_output(['soxi', '-s', output_file], stderr=subprocess.STDOUT))

    if len(text) < 4:
        return
    if frames / 16000 > 10:
        return
    if int(frames / 16000 * 1000 / 10 / 2) < len(text):
        return

    return output_file + "," + str(os.path.getsize(output_file)) + "," + text + "\n"


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

for i, async_result in enumerate(async_results):
    async_result.wait()
    print("Done for", i)

print("\nStart analysing TEXT files ...")

read_results = pool.map(text_read, args_list)

print("Done\n")

train_csv = open(mode_value + "-train.csv", "w+")
test_csv = open(mode_value + "-test.csv", "w+")
dev_csv = open(mode_value + "-dev.csv", "w+")

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
