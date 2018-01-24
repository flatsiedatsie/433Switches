#!/usr/bin/env python3
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
import warnings
import pigpio
import contextlib


class rfrx():
	#print("in the rx class")
	"""
	A class to read the wireless codes transmitted by 433 MHz
	wireless fobs.
	"""
	def __init__(self, pi, name, gpio, callback=None, min_bits=8, max_bits=32, glitch=150):
		print("press the button a few times")
		"""
		Instantiate with the Pi and the GPIO connected to the wireless
		receiver.

		If specified the callback will be called whenever a new code
		is received.  The callback will be passed the code, the number
		of bits, the length (in us) of the gap, short pulse, and long
		pulse.

		Codes with bit lengths outside the range min_bits to max_bits
		will be ignored.

		A glitch filter will be used to remove edges shorter than
		glitch us long from the wireless stream.  This is intended
		to remove the bulk of radio noise.
		"""
		
		self.name = name
		self.pi = pi
		self.gpio = gpio
		#print(str(self.gpio))
		self.cb = callback
		self.min_bits = min_bits
		self.max_bits = max_bits
		self.glitch = glitch
		#print(glitch)

		self._in_code = False
		self._edge = 0
		self._code = 0
		self._gap = 0

		self._ready = False

		pi.set_mode(gpio, pigpio.INPUT)
		pi.set_glitch_filter(gpio, glitch)

		#print(pi)
		
		self._last_edge_tick = pi.get_current_tick()
		self._cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cbf)

	def _timings(self, e0, e1):
		"""
		Accumulates the short and long pulse length so that an
		average short/long pulse length can be calculated. The
		figures may be used to tune the transimission settings.
		"""
		if e0 < e1:
			shorter = e0
			longer = e1
		else:
			shorter = e1
			longer = e0

		if self._bits:
			self._t0 += shorter
			self._t1 += longer
		else:
			self._t0 = shorter
			self._t1 = longer

		self._bits += 1

	def _calibrate(self, e0, e1):
		"""
		The first pair of pulses is used as the template for
		subsequent pulses.  They should be one short, one long, not
		necessarily in that order.  The ratio between long and short
		should really be 2 or more.  If less than 1.5 the pulses are
		assumed to be noise.
		"""
		self._bits = 0
		self._timings(e0, e1)
		self._bits = 0

		ratio = float(self._t1)/float(self._t0)

		if ratio < 1.5:
			self._in_code = False
			print("noise")

		slack0 = int(0.3 * self._t0)
		slack1 = int(0.2 * self._t1)

		self._min_0 = self._t0 - slack0
		self._max_0 = self._t0 + slack0
		self._min_1 = self._t1 - slack1
		self._max_1 = self._t1 + slack1

	def _test_bit(self, e0, e1):
		"""
		Returns the bit value represented by the sequence of pulses.

		0: short long
		1: long short
		2: illegal sequence
		"""
		self._timings(e0, e1)

		if	( (self._min_0 < e0 < self._max_0) and
				 (self._min_1 < e1 < self._max_1) ):
			#print("short long")
			return 0
		elif ( (self._min_0 < e1 < self._max_0) and
				 (self._min_1 < e0 < self._max_1) ):
			#print("long short")
			return 1
		else:
			#print("illegal sequence")
			return 2


	def _cbf(self, g, l, t):
		"""
		Accumulates the code from pairs of short/long pulses.
		The code end is assumed when an edge greater than 5 ms
		is detected.
		"""
		#print("edge");
		edge_len = pigpio.tickDiff(self._last_edge_tick, t)
		self._last_edge_tick = t

		if edge_len > 3000: # 5000 us, 5 ms.

			if self._in_code:
				if self.min_bits <= self._bits <= self.max_bits:
					self._lbits = self._bits
					self._lcode = self._code
					self._lgap = self._gap
					self._lt0 = int(self._t0/self._bits)
					self._lt1 = int(self._t1/self._bits)
					self._ready = True
					if self.cb is not None:
						self.cb(self.name, self._lcode, self._lbits, self._lgap, self._lt0, self._lt1)

			self._in_code = True
			self._gap = edge_len
			self._edge = 0
			self._bits = 0
			self._code = 0

		elif self._in_code:

			if self._edge == 0:
				self._e0 = edge_len
			elif self._edge == 1:
				self._calibrate(self._e0, edge_len)

			if self._edge % 2: # Odd edge.

				bit = self._test_bit(self._even_edge_len, edge_len)
				self._code = self._code << 1
				if bit == 1:
					self._code += 1
				elif bit != 0:
					self._in_code = False

			else: # Even edge.

				self._even_edge_len = edge_len

			self._edge += 1

	def ready(self):
		"""
		Returns True if a new code is ready.
		"""
		#print("code ready")
		return self._ready

	def code(self):
		"""
		Returns the last receieved code.
		"""
		self._ready = False
		return self._lcode

	def details(self):
		"""
		Returns details of the last receieved code.  The details
		consist of the code, the number of bits, the length (in us)
		of the gap, short pulse, and long pulse.
		"""
		self._ready = False
		return self._lcode, self._lbits, self._lgap, self._lt0, self._lt1

	def cancel(self):
		"""
		Cancels the wireless code receiver.
		"""
		if self._cb is not None:
			self.pi.set_glitch_filter(self.gpio, 0) # Remove glitch filter.
			self._cb.cancel()
			self._cb = None


class rftx():
	#print("in the tx function") 
	"""
	A class to transmit the wireless codes sent by 433 MHz
	wireless fobs.
	"""

	def __init__(self, pi, gpio, repeats, bits, gap, t0, t1):
	#def __init__(self, pi, gpio, repeats=6, bits=24, gap=9000, t0=300, t1=900):
	#def __init__(self, gpio, repeats=6, bits=28, gap=4955, t0=328, t1=974):
		"""
		Instantiate with the Pi and the GPIO connected to the wireless
		transmitter.

		The number of repeats (default 6) and bits (default 24) may
		be set.

		The pre-/post-amble gap (default 9000 us), short pulse length
		(default 300 us), and long pulse length (default 900 us) may
		be set.
		"""
		#print("starting the transmission")
		self.pi = pi
		self.gpio = gpio
		#print(str(gpio))
		#print("gpio = " . int(self.gpio))
		#self.code = code
		self.repeats = repeats
		#print(str(self.repeats))
		self.bits = bits
		#print(str(bits))
		self.gap = gap
		#print(str(gap))
		self.t0 = t0
		#print(str(t0))
		self.t1 = t1
		#print(str(t1))
		
		self._make_waves()

		pi.set_mode(gpio, pigpio.OUTPUT)

	def _make_waves(self):
		"""
		Generates the basic waveforms needed to transmit codes.
		"""
		wf = []
		wf.append(pigpio.pulse(1<<self.gpio, 0, self.t0))
		wf.append(pigpio.pulse(0, 1<<self.gpio, self.gap))
		self.pi.wave_add_generic(wf)
		self._amble = self.pi.wave_create()

		wf = []
		wf.append(pigpio.pulse(1<<self.gpio, 0, self.t0))
		wf.append(pigpio.pulse(0, 1<<self.gpio, self.t1))
		self.pi.wave_add_generic(wf)
		self._wid0 = self.pi.wave_create()

		wf = []
		wf.append(pigpio.pulse(1<<self.gpio, 0, self.t1))
		wf.append(pigpio.pulse(0, 1<<self.gpio, self.t0))
		self.pi.wave_add_generic(wf)
		self._wid1 = self.pi.wave_create()

	def set_repeats(self, repeats):
		"""
		Set the number of code repeats.
		"""
		if 1 < repeats < 100:
			self.repeats = repeats

	def set_bits(self, bits):
		"""
		Set the number of code bits.
		"""
		if 5 < bits < 65:
			self.bits = bits

	def set_timings(self, gap, t0, t1):
		"""
		Sets the code gap, short pulse, and long pulse length in us.
		"""
		self.gap = gap
		self.t0 = t0
		self.t1 = t1

		self.pi.wave_delete(self._amble)
		self.pi.wave_delete(self._wid0)
		self.pi.wave_delete(self._wid1)

		self._make_waves()

	def send(self, code):
		"""
		Transmits the code (using the current settings of repeats,
		bits, gap, short, and long pulse length).
		"""     
		chain = [self._amble, 255, 0]

		bit = (1<<(self.bits-1))
		for i in range(self.bits):
			if code & bit:
				chain += [self._wid1]
			else:
				chain += [self._wid0]
			bit = bit >> 1

		chain += [self._amble, 255, 1, self.repeats, 0]

		self.pi.wave_chain(chain)

		while self.pi.wave_tx_busy():
			time.sleep(0.1)

	def cancel(self):
		"""
		Cancels the wireless code transmitter.
		"""
		self.pi.wave_delete(self._amble)
		self.pi.wave_delete(self._wid0)
		self.pi.wave_delete(self._wid1)

	
	
	
def exithandler(signal, frame):
	database.close()
	pi.stop()
	sys.exit(11)


def play(args, database):
	#print("using GPIO pin:")
	#print(args.txpin)
	#print(args.recordingName)
	recording = str(args.recordingName[0])
	#database = shelve.open("DomoticzRFSwitchesDatabase")
	
	pin = int(args.txpin)
	
	#print("playing: " + recording)
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
	tx=rftx(pi, gpio=17, repeats=6, bits=bits, gap=gap, t0=t0, t1=t1)
	#try:
	tx.send(code)
	#time.sleep(1)
	#tx.cancel()
	#except:
	#print("playing failed, unable to transmit")
	#tx.cancel() # Cancel the transmitter.
	pi.stop() # Disconnect from local Pi.
	#sys.exit(12)


def rx_callback(name, code, bits, gap, t0, t1):
	global bitLengthFound
	#print(args.recordingName)
	#recording = str(args.recordingName)
	recording = str(name)
	#print("code={} bits={} (gap={} t0={} t1={})" . format(code, bits, gap, t0, t1))
	if(bits > bitLengthFound): #try to get as long as possible of a code
		print("saving longer bitlength code")
		database[recording] = [str(code), str(bits), str(gap), str(t0), str(t1)]
		bitLengthFound = bits


def record(args, database):	
	#try:
	pi = pigpio.pi()
	print("yoyo")
	print(str(args.recordingName))
	rx=rfrx(pi, name=args.recordingName, gpio=args.rxpin, callback=rx_callback)
	time.sleep(5)
	pi.stop()
	sys.exit(13)


def dump(args, database):
	for recordingName in sorted(database.keys()):
		print(recordingName)


def main():
	print("preparing..")
	global bitLengthFound
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

	databaseFile=os.path.join(os.environ['HOME'],'RFSwitches3')
	global database
	database = shelve.open(databaseFile)
	args.func(args, database)
	database.close()
	print("done")
	#pi.stop() # Disconnect from local Pi.

	sys.exit(0)

if __name__ == '__main__':
	main()	
	