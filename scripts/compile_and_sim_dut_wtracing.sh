#!/bin/bash
# Copyright 2020 Google LLC
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

# Move to target CORE dir
cd $SRC/circuits/$CORE

################################################################################
################################################################################
## Re-build simulation EXE with VCD tracing enabled
################################################################################
################################################################################
echo "========================================================================="
echo "Re-building HW model with VCD tracing enabled ..."
echo "-------------------------------------------------------------------------"

# Verilate hardware
echo "Verilating hardware ..."
make verilate
echo "-------------------------------------------------------------------------"
echo "Done!"
echo "-------------------------------------------------------------------------"

# Set compilers
echo "Setting compiler/linker flags ..."
export CC="clang"
export CXX="clang++"
export CCC="clang++"
export VLT_CXX="clang++"
export CFLAGS=""
export CXXFLAGS=""
export VLT_CXXFLAGS=""
export LDFLAGS=""

# Print compiler/linker flags
echo "Compiler/Linker Flags:"
echo "CC=$CC"
echo "CXX=$CXX"
echo "CFLAGS=$CFLAGS"
echo "CXXFLAGS=$CXXFLAGS"
echo "VLT_CXXFLAGS=$VLT_CXXFLAGS"
echo "LDFLAGS=$LDFLAGS"
echo "-------------------------------------------------------------------------"
echo "Done!"
echo "-------------------------------------------------------------------------"

# Compile SW model of HW
echo "Compiling SW model of HW ..."
make exe
echo "-------------------------------------------------------------------------"
echo "Done!"

################################################################################
################################################################################
## Generate VCD traces
################################################################################
################################################################################
echo "========================================================================="
echo "Generating VCD traces of AFLGO inputs ..."
echo "-------------------------------------------------------------------------"
# iterate over test files generated by AFLGO
cd $FUZZ_RESULTS_DIR && mkdir -p vcd && cd vcd
for test_file in ../afl_out/queue/*; do
    echo "Generating VCD trace for: $test_file ..."
    $SRC/circuits/$CORE/bin/V$CORE $test_file > /dev/null
done
echo "-------------------------------------------------------------------------"
echo "Done!"

################################################################################
################################################################################
## Clean up build
################################################################################
################################################################################
echo "========================================================================="
echo "Cleaning up ..."
echo "-------------------------------------------------------------------------"
cd $SRC/circuits/$CORE
make cleanall
echo "-------------------------------------------------------------------------"
echo "Done!"
echo "========================================================================="
exit 0
