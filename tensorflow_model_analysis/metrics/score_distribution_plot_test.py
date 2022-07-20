# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for confusion matrix plot."""

import apache_beam as beam
from apache_beam.testing import util
import numpy as np
import tensorflow as tf
from tensorflow_model_analysis.eval_saved_model import testutil
from tensorflow_model_analysis.metrics import metric_types
from tensorflow_model_analysis.metrics import metric_util
from tensorflow_model_analysis.metrics import score_distribution_plot


class ScoreDistributionPlotTest(testutil.TensorflowModelAnalysisTest):

  def testScoreDistributionPlot(self):
    computations = score_distribution_plot.ScoreDistributionPlot(
        num_thresholds=4).computations()
    histogram = computations[0]
    matrices = computations[1]
    plot = computations[2]

    example1 = {
        'labels': np.array([0.0]),
        'predictions': np.array([0.0]),
        'example_weights': np.array([1.0]),
    }
    example2 = {
        'labels': np.array([0.0]),
        'predictions': np.array([0.5]),
        'example_weights': np.array([1.0]),
    }
    example3 = {
        'labels': np.array([0.0]),
        'predictions': np.array([0.3]),
        'example_weights': np.array([1.0]),
    }
    example4 = {
        'labels': np.array([0.0]),
        'predictions': np.array([0.9]),
        'example_weights': np.array([1.0]),
    }

    with beam.Pipeline() as pipeline:
      # pylint: disable=no-value-for-parameter
      result = (
          pipeline
          | 'Create' >> beam.Create([example1, example2, example3, example4])
          | 'Process' >> beam.Map(
              metric_util.to_standard_metric_inputs, include_labels=False)
          | 'AddSlice' >> beam.Map(lambda x: ((), x))
          | 'ComputeHistogram' >> beam.CombinePerKey(histogram.combiner)
          | 'ComputeMatrices' >> beam.Map(
              lambda x: (x[0], matrices.result(x[1])))  # pyformat: ignore
          | 'ComputePlot' >> beam.Map(lambda x: (x[0], plot.result(x[1]))))

      # pylint: enable=no-value-for-parameter

      def check_result(got):
        try:
          self.assertLen(got, 1)
          got_slice_key, got_plots = got[0]
          self.assertEqual(got_slice_key, ())
          self.assertLen(got_plots, 1)
          key = metric_types.PlotKey(name='score_distribution_plot')
          self.assertIn(key, got_plots)
          got_plot = got_plots[key]
          self.assertProtoEquals(
              """
              matrices {
                threshold: -1e-06
                true_positives: 4.0
              }
              matrices {
                true_negatives: 1.0
                true_positives: 3.0
              }
              matrices {
                threshold: 0.25
                true_negatives: 1.0
                true_positives: 3.0
              }
              matrices {
                threshold: 0.5
                true_negatives: 3.0
                true_positives: 1.0
              }
              matrices {
                threshold: 0.75
                true_negatives: 3.0
                true_positives: 1.0
              }
              matrices {
                threshold: 1.0
                true_negatives: 4.0
              }
          """, got_plot)

        except AssertionError as err:
          raise util.BeamAssertException(err)

      util.assert_that(result, check_result, label='result')


if __name__ == '__main__':
  tf.test.main()
