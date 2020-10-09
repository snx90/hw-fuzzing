# Copyright 2020 Timothy Trippel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""HW fuzzing opcodes to be used with bus-level AFL testbench harness."""

from enum import IntEnum

ENDIANNESS = "little"  # how to interpret bytes from STDIN
OPCODE_SIZE = 1  # number of opcode bytes to read from STDIN
WAIT_OPCODE_THRESHOLD = 85
RW_OPCODE_THRESHOLD = 170


class HWFuzzOpcode(IntEnum):
  """Hardware fuzzer opcode derived from AFL generated inputs."""
  wait = 1
  read = 2
  write = 3