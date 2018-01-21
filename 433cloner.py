#!/usr/bin/env python
'''

This code is a mix of two things:
- The RF Sniffer project by Jesper Derehag. Licence is below.
- The 433 cloner code form the PiGPIO project, which is public domain.


Copyright (c) 2017, Jesper Derehag
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from __future__ import print_function
import argparse
import os
import shelve
import time
import signal
import sys
#import warnings

try:
    import pigpio
    import _433
except:
    print("The PiGPIO library does not seem to be installed.")

def exithandler(signal, frame):
    database.close()
    pi.stop()
    sys.exit(0)


def play(args, database):
    print("using GPIO pin:")
    print(args.txpin)
    #print(args.recordingName)
    recording = str(args.recordingName[0])
    #database = shelve.open("DomoticzRFSwitchesDatabase")
    
    pin = int(args.txpin)
    
    print("playing: " + recording)
    repeats = 6;
    code = int(database[recording][0])
    bits = int(database[recording][1])
    gap = int(database[recording][2])
    t0 = int(database[recording][3])
    t1 = int(database[recording][4])
    
    #print(str(code))
    #print(bits)
    #print(gap)
    #print(t0)
    #print(t1)
    
    pi = pigpio.pi()
    tx=_433.tx(pi, gpio=17, repeats=6, bits=bits, gap=gap, t0=t0, t1=t1)
    try:
        tx.send(code)
        time.sleep(2)
        tx.cancel()
    except:
        print("playing failed, unable to transmit")
        #tx.cancel() # Cancel the transmitter.
        pi.stop() # Disconnect from local Pi.
        sys.exit(0)


def rx_callback(code, bits, gap, t0, t1):
    global bitLengthFound
    #print(args.recordingName)
    recording = str(args.recordingName)
    print("code={} bits={} (gap={} t0={} t1={})" . format(code, bits, gap, t0, t1))
    if(bits > bitLengthFound): #try to get as long as possible of a code
        print("saving longer bitlength code")
        database[recording] = [str(code), str(bits), str(gap), str(t0), str(t1)]
        bitLengthFound = bits


def record(args, database):
    try:
        pi = pigpio.pi()
        rx=_433.rx(pi, gpio=args.rxpin, callback=rx_callback)
        time.sleep(5)
    except:
        rx.cancel()
        pi.stop()
        sys.exit(0)


def dump(args, database):
    for recordingName in sorted(database.keys()):
        print(recordingName)


print("preparing..")
bitLengthFound = 0
signal.signal(signal.SIGINT, exithandler)
fc = argparse.ArgumentDefaultsHelpFormatter
parser = argparse.ArgumentParser(add_help=True, formatter_class=fc)

subparsers = parser.add_subparsers(help='sub-command help')

parser.add_argument('--rxpin', type=int, default=27, help=('The RPi GPIO pin where the RF receiver is attached (default:27)'))

parser.add_argument('--txpin', type=int, default=17, help=('The RPi GPIO pin where the RF transmitter is attached (default:17)'))

#parser.add_argument('-b', '--databasedb', dest='databasedb', default=os.path.join(os.environ['HOME'], 'RFSwitches.db'))

# Record subcommand
parser_record = subparsers.add_parser('record', help='Record an RF signal')
parser_record.add_argument('recordingName')
parser_record.set_defaults(func=record)

# Play subcommand
parser_play = subparsers.add_parser('play', help=('Send a previously recorded RF signal'))
parser_play.add_argument('recordingName', nargs='*')
parser_play.set_defaults(func=play)

# Dump subcommand
parser_dump = subparsers.add_parser('dump', help=('Dumps the already recorded RF signals'))
parser_dump.set_defaults(func=dump)

args = parser.parse_args()

database = shelve.open("RFSwitchesDatabase")
args.func(args, database)
database.close()
print("done")
#pi.stop() # Disconnect from local Pi.


