import getopt
import os
import re
import subprocess
import sys

opts, args = getopt.getopt(sys.argv[1:], 'hs:t:')
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

wav_output_directory = os.getcwd() + "/wav/"

if not os.path.exists(wav_output_directory):
    os.makedirs(wav_output_directory)

data_output_directory = os.getcwd() + "/swb/"

if not os.path.exists(data_output_directory):
    os.makedirs(data_output_directory)

with open(opts['-s']) as scp_file:
    for index, line in enumerate(scp_file):
        scp = line.split()
        output_file = wav_output_directory + scp[0] + ".wav"
        subprocess.run([scp[1], scp[2], scp[3], scp[4], scp[5], scp[6], scp[7], output_file])

head = "wav_filename,wav_filesize,transcript\n"

train_csv = open("swb-train.csv", "w+")
train_csv.write(head)

brackets = re.compile(r'[.+]')

punctuations = r"""!"#$%&()*+,-./:;<=>?@[\]^_`{|}~"""
punctuation = re.compile('[%s]' % re.escape(punctuations))


def ns_to_ms(time_point):
    return int(time_point) / 100


with open(opts['-t']) as text_file:
    for index, line in enumerate(text_file):
        prefix = line[0:23]
        prefix = prefix.split("_")
        time = prefix[1].split("-")

        input_file = wav_output_directory + prefix[0] + ".wav"
        output_file = data_output_directory + "{0:06d}".format(index) + ".wav"

        length = float(subprocess.check_output(['soxi', '-D', input_file], stderr=subprocess.STDOUT))

        start_position = str(ns_to_ms(time[0]))
        end_position = ns_to_ms(time[1]) if ns_to_ms(time[1]) < length else length
        end_position = "=" + str(end_position)
        subprocess.run(["sox", "-v", "0.80", input_file, "-e", "signed-integer", output_file, "trim", start_position, end_position])

        text = line[23:]
        text = text.replace("&", " and ")

        text = text.lower()

        text = brackets.sub('', text)
        text = punctuation.sub('', text)
        text = text.replace("  ", " ")
        text = text.strip()

        frames = int(subprocess.check_output(['soxi', '-s', output_file], stderr=subprocess.STDOUT))

        if len(text) < 4:
            continue
        if frames / 16000 > 10:
            continue
        if int(frames / 16000 * 1000 / 10 / 2) < len(text):
            continue

        text = output_file + "," + str(os.path.getsize(output_file)) + "," + text + "\n"
        train_csv.write(text)

train_csv.close()
