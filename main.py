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

SAMPLE_RATE = 16000

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
    brackets = re.compile(r'\[.+\]')
else:
    brackets = re.compile(r'<.+>')

head = "wav_filename,wav_filesize,transcript\n"
punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""
punctuation = re.compile('[%s]' % re.escape(punctuations))


def ns_to_ms(ns_time):
    return int(ns_time) / 100


def mkdir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


for directory in output_directories:
    mkdir(directory)

if mode != mode.WSJ:
    mkdir(current_directory + "/wav")


def scp_file_read(arg):
    path, output = arg

    sub_process_arg_list = []

    if mode == Mode.SWB:

        with open(path + "/wav.scp") as scp_file:
            for line in scp_file:
                scp = line.split()
                output_file = "wav/" + scp[0] + ".wav"
                sub_process_arg_list.append([scp[1], scp[2], scp[3], scp[4], scp[5], scp[6], scp[7], output_file])

    elif mode == Mode.WSJ:
        with open(path + "/wav.scp") as scp_file:
            for index, line in enumerate(scp_file):
                scp = line.split()
                output_file = output + "/{0:06d}".format(index) + ".wav"
                sub_process_arg_list.append([scp[1], scp[2], scp[3], scp[4], output_file])

    elif mode == Mode.AMI:
        with open(path + "/wav.scp") as scp_file:
            for line in scp_file:
                scp = line.split()
                output_file = "wav/" + scp[0] + ".wav"
                sub_process_arg_list.append(["cp", scp[8], output_file])

    return sub_process_arg_list


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
    text = ""
    output_file = ""
    line, index, output_directory = arg

    if mode == mode.SWB:

        time = line[10:23].split("-")

        input_file = "wav/" + line[0:9] + ".wav"
        output_file = output_directory + "/{0:06d}".format(index) + ".wav"

        length = float(subprocess.check_output(['soxi', '-D', input_file], stderr=subprocess.STDOUT))

        start_position = str(ns_to_ms(time[0]))
        end_position = ns_to_ms(time[1]) if ns_to_ms(time[1]) < length else length
        end_position = "=" + str(end_position)
        subprocess.run(["sox", input_file, "-e", "signed-integer", "-r", "16000",
                        output_file, "trim", start_position, end_position])

        text = line[23:]
        text = brackets.sub('', text)

        text = re.sub(r' (\d+)(000)(S|ST|ND|RD|TH|)', r' \1 THOUSAND\3 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' (\d+)0(\d\d)(S|ST|ND|RD|TH|)', r' \1 THOUSAND AND \2\3 ',
                      text)  # RN 2012-02-20 edited this line
        text = re.sub(r' (\d+)(\d\d\d)(S|ST|ND|RD|TH|)', r' \1 THOUSAND \2\3 ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' (\d)(00)(S|ST|ND|RD|TH|)', r' \1 HUNDRED\3 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' (\d)(\d\d)(S|ST|ND|RD|TH|)', r' \1 HUNDRED AND \2\3 ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' 11(S|ST|ND|RD|TH|)', r' ELEVEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 12(S|ST|ND|RD|TH|) ', r' TWELVE\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 13(S|ST|ND|RD|TH|) ', r' THIRTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 14(S|ST|ND|RD|TH|) ', r' FOURTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 15(S|ST|ND|RD|TH|) ', r' FIFTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 16(S|ST|ND|RD|TH|) ', r' SIXTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 17(S|ST|ND|RD|TH|) ', r' SEVENTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 18(S|ST|ND|RD|TH|) ', r' EIGHTEEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 19(S|ST|ND|RD|TH|) ', r' NINETEEN\1 ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' 10 ', r' TEN ', text)
        text = re.sub(r' 20 ', r' TWENTY ', text)
        text = re.sub(r' 30 ', r' THIRTY ', text)
        text = re.sub(r' 40 ', r' FOURTY ', text)
        text = re.sub(r' 50 ', r' FIFTY ', text)
        text = re.sub(r' 60 ', r' SIXTY ', text)
        text = re.sub(r' 70 ', r' SEVENTY ', text)
        text = re.sub(r' 80 ', r' EIGHTY ', text)
        text = re.sub(r' 90 ', r' NINETY ', text)

        text = re.sub(r' 11 ', r' ELEVEN ', text)
        text = re.sub(r' 12 ', r' TWELVE ', text)
        text = re.sub(r' 11 ', r' THIRTEEN ', text)
        text = re.sub(r' 11 ', r' FOURTEEN ', text)
        text = re.sub(r' 11 ', r' FIFTEEN ', text)
        text = re.sub(r' 11 ', r' SIXTEEN ', text)
        text = re.sub(r' 11 ', r' SEVENTEEN ', text)
        text = re.sub(r' 11 ', r' EIGHTEEN ', text)
        text = re.sub(r' 11 ', r' NINETEEN ', text)
        text = re.sub(r' 11 ', r' TWENTY ', text)

        text = re.sub(r' 20S ', r' TWENTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 30S ', r' THIRTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 40S ', r' FOURTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 50S ', r' FIFTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 60S ', r' SIXTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 70S ', r' SEVENTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 80S ', r' EIGHTIES ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 90S ', r' NINETIES ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' 20TH ', r' TWENTIETH ', text)
        text = re.sub(r' 30TH ', r' THIRTITH ', text)
        text = re.sub(r' 40TH ', r' FOURTIETH ', text)
        text = re.sub(r' 50TH ', r' FIFTIETH ', text)
        text = re.sub(r' 60TH ', r' SIXTIETH ', text)
        text = re.sub(r' 70TH ', r' SEVENTIETH ', text)
        text = re.sub(r' 80TH ', r' EIGHTIETH ', text)
        text = re.sub(r' 90TH ', r' NINETIETH ', text)

        text = re.sub(r' 2(\d)(S|ST|ND|RD|TH|) ', r' TWENTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 3(\d)(S|ST|ND|RD|TH|) ', r' THIRTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 4(\d)(S|ST|ND|RD|TH|) ', r' FOURTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 5(\d)(S|ST|ND|RD|TH|) ', r' FIFTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 6(\d)(S|ST|ND|RD|TH|) ', r' SIXTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 7(\d)(S|ST|ND|RD|TH|) ', r' SEVENTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 8(\d)(S|ST|ND|RD|TH|) ', r' EIGHTY \1\2 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 9(\d)(S|ST|ND|RD|TH|) ', r' NINETY \1\2 ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' 0(\d)(ST|ND|RD|TH|) ', r' \1\2 ', text)

        text = re.sub(r' 1ST ', r' FIRST ', text)
        text = re.sub(r' 2ND ', r' SECOND ', text)
        text = re.sub(r' 3RD ', r' THIRD ', text)
        text = re.sub(r' 4TH ', r' FOURTH ', text)
        text = re.sub(r' 5TH ', r' FIFTH ', text)
        text = re.sub(r' 6TH ', r' SIXTH ', text)
        text = re.sub(r' 7TH ', r' SEVENTH ', text)
        text = re.sub(r' 8TH ', r' EIGHTH ', text)
        text = re.sub(r' 9TH ', r' NINTH ', text)
        text = re.sub(r' 10TH ', r' TENTH ', text)

        text = re.sub(r' 1 ', r' ONE ', text)
        text = re.sub(r' 2(S|) ', r' TWO\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 3(S|) ', r' THREE\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 4(S|) ', r' FOUR\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 5(S|) ', r' FIVE\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 6(S|) ', r' SIX\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 7(S|) ', r' SEVEN\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 8(S|) ', r' EIGHT\1 ', text)  # RN 2012-02-20 edited this line
        text = re.sub(r' 9(S|) ', r' NINE\1 ', text)  # RN 2012-02-20 edited this line

        text = re.sub(r' 1/2 ', r' A HALF', text)
        text = re.sub(r' 1/3 ', r' A THIRD ', text)
        text = re.sub(r' 1/4 ', r' A QUARTER ', text)

        text = re.sub(r'0', r' ZERO ', text)

        text = text.replace("&", " and")

    elif mode == mode.AMI:

        time = line.split()[0]
        time = time[-15:].split("_")
        input_file = "wav/" + line[0:15] + ".wav"

        output_file = output_directory + "/{0:06d}".format(index) + ".wav"

        length = float(subprocess.check_output(['soxi', '-D', input_file], stderr=subprocess.STDOUT))

        start_position = str(ns_to_ms(time[0]))
        end_position = ns_to_ms(time[1]) if ns_to_ms(time[1]) < length else length
        end_position = "=" + str(end_position)

        subprocess.run(["sox", input_file, output_file, "trim", start_position, end_position])

        text = line.replace(line.split()[0], "").strip()

    elif mode == mode.WSJ:

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

        text = brackets.sub('', text)
        text = text.replace("&AMPERSAND", "and")

        output_file = output_directory + "/{0:06d}".format(index) + ".wav"

    text = text.lower()

    text = punctuation.sub('', text)
    text = text.replace("  ", " ")
    text = text.strip()

    frames = int(subprocess.check_output(['soxi', '-s', output_file], stderr=subprocess.STDOUT))

    if len(text) < 3:
        return
    if frames / SAMPLE_RATE > 10:
        return
    if int(frames / SAMPLE_RATE * 1000 / 10 / 2) < len(text):
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
