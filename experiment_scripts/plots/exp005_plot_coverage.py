#!/usr/bin/env python3
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

import argparse
import collections
import glob
import itertools
import os
import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
# import numpy as np
import pandas as pd
import seaborn as sns
from hwfutils.string_color import color_str_green as green
from hwfutils.string_color import color_str_red as red
from hwfutils.string_color import color_str_yellow as yellow

# from scipy import stats

# ------------------------------------------------------------------------------
# Plot parameters
# ------------------------------------------------------------------------------
MARKER_SIZE = 5
ZSCORE_THRESHOLD = 3

# ------------------------------------------------------------------------------
# Plot labels
# ------------------------------------------------------------------------------
TIME_LABEL = "Time (s)"
TOPLEVEL_LABEL = "Core"
GRAMMAR_LABEL = "Grammar"
COVERAGE_TYPE_LABEL = "Coverage"
COVERAGE_LABEL = "Coverage (%)"
HW_LINE_COVERAGE_LABEL = "HW Line (VLT)"
SW_LINE_COVERAGE_LABEL = "SW Line (kcov)"
SW_REGION_COVERAGE_LABEL = "SW Region (LLVM)"

# ------------------------------------------------------------------------------
# Other Labels
# ------------------------------------------------------------------------------
AFL_TEST_ID_LABEL = "Test-ID"

# ------------------------------------------------------------------------------
# Experiment Parameters
# ------------------------------------------------------------------------------
# EXPERIMENT_BASE_NAME = "exp010-cpp-afl-%s-%s-%s-%s"
EXPERIMENT_BASE_NAME = "exp011-cpp-afl-%s-%s-%s-%s"
TOPLEVELS = ["aes", "hmac", "kmac", "rv_timer"]
OPCODE_TYPES = ["constant", "mapped"]
INSTR_TYPES = ["variable", "fixed"]
# TERMINATE_TYPES = ["invalidop", "never"]
TERMINATE_TYPES = ["never"]
TRIALS = range(0, 5)

# ------------------------------------------------------------------------------
# Other defines
# ------------------------------------------------------------------------------
TERMINAL_ROWS, TERMINAL_COLS = os.popen('stty size', 'r').read().split()
LINE_SEP = "=" * int(TERMINAL_COLS)

COUNT = 0


@dataclass
class FuzzingData:
  toplevel: str = ""
  opcode_type: str = ""
  instr_type: str = ""
  terminate_type: str = ""
  trial_num: int = -1
  afl_data_path: str = ""
  cov_data_path: str = ""

  def __post_init__(self):
    self.afl_data = self._load_afl_data()
    self.kcov_data = self._load_cov_data("kcov")
    self.llvm_cov_data = self._load_cov_data("llvm_cov")
    self.vlt_cov_data = self._load_cov_data("vlt_cov")

  def _load_afl_data(self):
    afl_glob_path = os.path.join(self.afl_data_path, "out",
                                 "afl_*_interactive", "plot_data")
    afl_plot_data_files = glob.glob(afl_glob_path)
    if len(afl_plot_data_files) != 1:
      print(red("ERROR: AFL plot_data file no found."))
      sys.exit(1)
    # Load data into Pandas DataFrame
    afl_df = self._load_csv_data(afl_plot_data_files[0])
    # Remove leading/trailing white space from column names
    afl_df = afl_df.rename(columns=lambda x: x.strip())
    # Adjust time stamps to be relative to start time
    afl_df.loc[:, "# unix_time"] -= afl_df.loc[0, "# unix_time"]
    # Set time as index
    afl_df = afl_df.set_index("# unix_time")
    return afl_df

  @staticmethod
  def _id_str_to_int(id_str):
    return int(id_str.lstrip("id:"))

  def _load_cov_data(self, cov_type):
    cov_data_path = "%s/logs/%s_cum.csv" % (self.cov_data_path, cov_type)
    if not os.path.exists(cov_data_path):
      print(red("ERROR: coverage data (%s) does not exist." % cov_data_path))
      sys.exit(1)
    # Load data into Pandas DataFrame
    cov_df = self._load_csv_data(cov_data_path)
    if abs(cov_df.shape[0] - int(self.afl_data.iloc[-1, 2])) > 1:
      print(cov_data_path)
      print(red("ERROR: coverage data is missing (%s). Aborting!" % cov_type))
      if cov_type == "vlt_cov":
        print()
        print()
        print()
    # TODO(ttrippel): remove this hack
    if cov_type == "vlt_cov":
      cov_df.drop(AFL_TEST_ID_LABEL, axis=1, inplace=True)
      cov_df.insert(0, AFL_TEST_ID_LABEL, list(range(cov_df.shape[0])))
    else:
      # Convert Test-ID labels to ints
      cov_df.loc[:,
                 AFL_TEST_ID_LABEL] = cov_df.loc[:, AFL_TEST_ID_LABEL].apply(
                     FuzzingData._id_str_to_int)
    # Set ID column as the row indicies
    cov_df = cov_df.set_index(AFL_TEST_ID_LABEL)
    return cov_df

  def _load_csv_data(self, csv_file):
    return pd.read_csv(csv_file,
                       delimiter=',',
                       index_col=None,
                       engine='python')

  @property
  def grammar(self):
    return "%s-%s-%s" % (self.opcode_type, self.instr_type,
                         self.terminate_type)


def get_paths_total_at_time(time, afl_data):
  while time not in afl_data.index:
    time -= 1
  return afl_data.loc[time, "paths_total"]


def get_cov_at_time(paths_total, cov_data, cov_data_key):
  if paths_total < cov_data.shape[0]:
    cov = cov_data.loc[paths_total, cov_data_key]
  else:
    cov = cov_data[cov_data_key][cov_data.index[-1]]
  return (cov * 100.0)


def get_vlt_cov_at_time(paths_total, vlt_cov_data):
  if paths_total < vlt_cov_data.shape[0]:
    vlt_cov = (float(vlt_cov_data.loc[paths_total, "Lines-Covered"]) /
               float(vlt_cov_data.loc[paths_total, "Total-Lines"]))
  else:
    last_index = vlt_cov_data.index[-1]
    vlt_cov = (float(vlt_cov_data["Lines-Covered"][last_index]) /
               float(vlt_cov_data["Total-Lines"][last_index]))
  return (vlt_cov * 100.0)


def build_avg_coverage_df(exp2data):
  print(yellow("Building average coverage dataframe ..."))
  # Create empty dictionary that will be used to create a Pandas DataFrame that
  # looks like the following:
  # +--------------------------------------------------------------------+
  # | toplevel | isa (grammar) | coverage type | time (s) | coverage (%) |
  # +--------------------------------------------------------------------+
  # |   ...    |        ...    |      ...      |   ...    |      ...     |
  coverage_dict = {
      TOPLEVEL_LABEL: [],
      GRAMMAR_LABEL: [],
      COVERAGE_TYPE_LABEL: [],
      TIME_LABEL: [],
      COVERAGE_LABEL: [],
  }
  for exp_name, fd_list in exp2data.items():
    anchor_fd = fd_list[0]
    for time, row in anchor_fd.afl_data.iterrows():
      # add circuit, grammar, and time values to dataframe row
      time_hours = float(time) / float(3600)
      for _ in range(3):
        coverage_dict[TOPLEVEL_LABEL].append(anchor_fd.toplevel)
        coverage_dict[GRAMMAR_LABEL].append(anchor_fd.grammar)
        coverage_dict[TIME_LABEL].append(time_hours)
      # compute average coverage at all points in time
      kcov_avg = 0
      llvm_cov_avg = 0
      vlt_cov_avg = 0
      for fd in fd_list:
        # get the paths_total at the current time
        paths_total = get_paths_total_at_time(time, fd.afl_data)
        # get coverage data
        kcov_avg += get_cov_at_time(paths_total, fd.kcov_data,
                                    "Line-Coverage-(%)")
        llvm_cov_avg += get_cov_at_time(paths_total, fd.llvm_cov_data,
                                        "Region-Coverage-(%)")
        vlt_cov_avg += get_vlt_cov_at_time(paths_total, fd.vlt_cov_data)
      kcov_avg /= len(fd_list)
      llvm_cov_avg /= len(fd_list)
      vlt_cov_avg /= len(fd_list)
      # add kcov data to dataframe row
      coverage_dict[COVERAGE_TYPE_LABEL].append(SW_LINE_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(kcov_avg)
      # add llvm-cov data to dataframe row
      coverage_dict[COVERAGE_TYPE_LABEL].append(SW_REGION_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(llvm_cov_avg)
      # add vlt-cov data to dataframe row
      coverage_dict[COVERAGE_TYPE_LABEL].append(HW_LINE_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(vlt_cov_avg)
  print(green("Done."))
  print(LINE_SEP)
  return pd.DataFrame.from_dict(coverage_dict)


def build_coverage_df(exp2data, trial):
  print(yellow("Building coverage dataframe ..."))
  # Create empty dictionary that will be used to create a Pandas DataFrame that
  # looks like the following:
  # +--------------------------------------------------------------------+
  # | toplevel | isa (grammar) | coverage type | time (s) | coverage (%) |
  # +--------------------------------------------------------------------+
  # |   ...    |        ...    |      ...      |   ...    |      ...     |
  coverage_dict = {
      TOPLEVEL_LABEL: [],
      GRAMMAR_LABEL: [],
      COVERAGE_TYPE_LABEL: [],
      TIME_LABEL: [],
      COVERAGE_LABEL: [],
  }

  # Add rows to the dataframe
  for exp_name, fd_list in exp2data.items():
    fd = fd_list[trial]
    for time, row in fd.afl_data.iterrows():
      cov_df_idx = row["paths_total"] - 1
      for _ in range(3):
        coverage_dict[TOPLEVEL_LABEL].append(fd.toplevel)
        coverage_dict[GRAMMAR_LABEL].append(fd.grammar)
        coverage_dict[TIME_LABEL].append(time)

      # Add kcov coverage
      if cov_df_idx < fd.kcov_data.shape[0]:
        kcov = fd.kcov_data.loc[cov_df_idx, "Line-Coverage-(%)"]
      else:
        # print(yellow("WARNING: missing indicies for kcov data."))
        kcov = fd.kcov_data["Line-Coverage-(%)"][fd.kcov_data.index[-1]]
      coverage_dict[COVERAGE_TYPE_LABEL].append(SW_LINE_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(kcov * 100.0)

      # Add LLVM coverage
      if cov_df_idx < fd.llvm_cov_data.shape[0]:
        llvm_cov = fd.llvm_cov_data.loc[cov_df_idx, "Region-Coverage-(%)"]
      else:
        # print(yellow("WARNING: missing indicies for llvm-cov data."))
        llvm_cov = fd.llvm_cov_data["Region-Coverage-(%)"][
            fd.llvm_cov_data.index[-1]]
      coverage_dict[COVERAGE_TYPE_LABEL].append(SW_REGION_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(llvm_cov * 100.0)

      # Add Verilator coverage
      if cov_df_idx < fd.vlt_cov_data.shape[0]:
        vlt_cov = (float(fd.vlt_cov_data.loc[cov_df_idx, "Lines-Covered"]) /
                   float(fd.vlt_cov_data.loc[cov_df_idx, "Total-Lines"]))
      else:
        # print(yellow("WARNING: missing indicies for vlt-cov data."))
        last_index = fd.vlt_cov_data.index[-1]
        vlt_cov = (float(fd.vlt_cov_data["Lines-Covered"][last_index]) /
                   float(fd.vlt_cov_data["Total-Lines"][last_index]))
      coverage_dict[COVERAGE_TYPE_LABEL].append(HW_LINE_COVERAGE_LABEL)
      coverage_dict[COVERAGE_LABEL].append(vlt_cov * 100.0)

  print(green("Done."))
  print(LINE_SEP)
  return pd.DataFrame.from_dict(coverage_dict)


def build_coverage_dfs(exp2data):
  coverage_dfs = []
  for trial in TRIALS:
    coverage_dfs.append(build_coverage_df(exp2data, trial))
  return coverage_dfs


def load_fuzzing_data(afl_data_root, cov_data_root):
  print(yellow("Loading data ..."))
  exp2data = collections.defaultdict(list)
  # TODO: change this to automatically extract names from a single exp. number
  # extract each data file into a Pandas dataframe
  isas = list(
      itertools.product(TOPLEVELS, OPCODE_TYPES, INSTR_TYPES, TERMINATE_TYPES))
  for toplevel, opcode_type, instr_type, terminate_type in isas:
    for trial in TRIALS:
      # Build complete path to data files
      exp_name_wo_trialnum = EXPERIMENT_BASE_NAME % (
          toplevel, opcode_type, instr_type, terminate_type)
      exp_name_wo_trialnum = exp_name_wo_trialnum.replace("_", "-")
      exp_name = "%s-%d" % (exp_name_wo_trialnum, trial)
      afl_data_path = os.path.join(afl_data_root, exp_name)
      cov_data_path = os.path.join(cov_data_root, exp_name)

      # Load fuzzing data into an object
      exp2data[exp_name_wo_trialnum].append(
          FuzzingData(toplevel, opcode_type, instr_type, terminate_type, trial,
                      afl_data_path, cov_data_path))
  return exp2data


def plot_coverage_vs_time(coverage_dfs):
  print(yellow("Generating plots ..."))
  cov_metrics = [
      SW_LINE_COVERAGE_LABEL, SW_REGION_COVERAGE_LABEL, HW_LINE_COVERAGE_LABEL
  ]
  num_cores = len(TOPLEVELS)
  num_cov_metrics = len(cov_metrics)
  sns.set_theme(context="notebook", style="darkgrid")
  fig, axes = plt.subplots(num_cov_metrics, num_cores, sharex=True)
  # sharey=True)
  for trial in range(len(coverage_dfs)):
    # Select experiment trial number
    cov_df = coverage_dfs[trial]
    for row in range(len(axes)):
      # select portion of data corresponding to current COVERAGE METRIC
      sub_cov_df = cov_df[cov_df[COVERAGE_TYPE_LABEL] == cov_metrics[row]]
      for col in range(len(axes[row])):
        # select portion of data corresponding to current core
        plt_df = sub_cov_df[sub_cov_df[TOPLEVEL_LABEL] == TOPLEVELS[col]]
        # sns.set_context("paper")
        curr_ax = sns.lineplot(data=plt_df,
                               x=TIME_LABEL,
                               y=COVERAGE_LABEL,
                               hue=GRAMMAR_LABEL,
                               ax=axes[row][col],
                               legend=False)
        if row == 0 and col == 0 and trial == 0:
          lines = curr_ax.get_lines()
        axes[row][col].set_title("Coverage = %s | Core = %s" %
                                 (cov_metrics[row], TOPLEVELS[col]))
  fig.legend(
      lines,
      [
          "Const. Opcode & Variable Frame",
          "Const. Opcode & Fixed Frame",
          "Mapped Opcode & Variable Frame",
          "Mapped Opcode & Fixed Frame",
      ],
      loc="lower center",
      ncol=4,
  )
  print(green("Done."))
  print(LINE_SEP)
  plt.show()


def plot_avg_coverage_vs_time(cov_df):
  print(yellow("Generating plots ..."))
  cov_metrics = [
      SW_LINE_COVERAGE_LABEL, SW_REGION_COVERAGE_LABEL, HW_LINE_COVERAGE_LABEL
  ]
  num_cores = len(TOPLEVELS)
  num_cov_metrics = len(cov_metrics)
  sns.set_theme(context="notebook", style="darkgrid")
  fig, axes = plt.subplots(num_cov_metrics,
                           num_cores,
                           sharex=True,
                           sharey=True)
  for row in range(len(axes)):
    # select portion of data corresponding to current COVERAGE METRIC
    sub_cov_df = cov_df[cov_df[COVERAGE_TYPE_LABEL] == cov_metrics[row]]
    for col in range(len(axes[row])):
      # select portion of data corresponding to current core
      plt_df = sub_cov_df[sub_cov_df[TOPLEVEL_LABEL] == TOPLEVELS[col]]
      # sns.set_context("paper")
      curr_ax = sns.lineplot(data=plt_df,
                             x=TIME_LABEL,
                             y=COVERAGE_LABEL,
                             hue=GRAMMAR_LABEL,
                             ax=axes[row][col],
                             legend=False)
      if row == 0 and col == 0:
        lines = curr_ax.get_lines()
      axes[row][col].set_title("Coverage = %s | Core = %s" %
                               (cov_metrics[row], TOPLEVELS[col]))
  fig.legend(
      lines,
      [
          "Const. Opcode & Variable Frame",
          "Const. Opcode & Fixed Frame",
          "Mapped Opcode & Variable Frame",
          "Mapped Opcode & Fixed Frame",
      ],
      loc="lower center",
      ncol=4,
  )
  print(green("Done."))
  print(LINE_SEP)
  plt.show()


def main(argv):
  parser = argparse.ArgumentParser(description="Plotting script for exp. 004.")
  parser.add_argument("afl_data_root")
  parser.add_argument("cov_data_root")
  args = parser.parse_args()

  # Load runtime data
  exp2data = load_fuzzing_data(args.afl_data_root, args.cov_data_root)
  avg_cov_df = build_avg_coverage_df(exp2data)
  # coverage_dfs = build_coverage_dfs(exp2data)

  # Compute stats

  # Plot data
  plot_avg_coverage_vs_time(avg_cov_df)
  # plot_coverage_vs_time(coverage_dfs)


if __name__ == "__main__":
  main(sys.argv[1:])
