#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

import os
import sys

from common.base_model_init import BaseModelInitializer

os.environ['KMP_AFFINITY'] = 'granularity=fine,compact,1,0'
os.environ['KMP_BLOCKTIME'] = '0'


class ModelInitializer(BaseModelInitializer):
    args = None
    custom_args = []

    def run_inference_sanity_checks(self, args, custom_args):
        if not args.input_graph:
            sys.exit("Please provide a path to the frozen graph directory"
                     " via the '--in-graph' flag.")
        if not args.data_location:
            sys.exit("Please provide a path to the data directory via the "
                     "'--data-location' flag.")
        if not args.single_socket and args.num_cores == -1:
            print("***Warning***: Running inference on all cores could degrade"
                  " performance. Pass '--single-socket' instead.\n")

    def __init__(self, args, custom_args, platform_util):
        self.args = args
        self.custom_args = custom_args
        platform_args = platform_util

        if args.mode == "inference":
            self.run_inference_sanity_checks(self.args, self.custom_args)
            num_cores_per_socket = platform_args.num_cores_per_socket()

            if args.single_socket:
                    args.num_inter_threads = 1
                    args.num_intra_threads = num_cores_per_socket
            else:
                args.num_inter_threads = platform_args.num_cpu_sockets()

            if args.num_cores == -1:
                args.num_intra_threads = \
                    num_cores_per_socket * args.num_inter_threads
            else:
                args.num_intra_threads = args.num_cores

            self.research_dir = os.path.join(args.model_source_dir, "research")
            script_path = "object_detection/inference/infer_detections.py"
            self.run_cmd = ("OMP_NUM_THREADS={} numactl -l -N 1 "
                            "python {} --input_tfrecord_paths {} "
                            "--inference_graph {} "
                            "--output_tfrecord_path="
                            "/tmp/ssd-mobilenet-record-out "
                            "--intra_op_parallelism_threads {} "
                            "--inter_op_parallelism_threads {} "
                            "--discard_image_pixels=True --inference_only").\
                format(str(args.num_intra_threads), script_path,
                       str(args.data_location), str(args.input_graph),
                       str(args.num_intra_threads),
                       str(args.num_inter_threads))
        else:
            sys.exit("Training is currently not supported.")

    def run(self):
        original_dir = os.getcwd()
        os.chdir(self.research_dir)
        self.run_command(self.run_cmd)
        os.chdir(original_dir)