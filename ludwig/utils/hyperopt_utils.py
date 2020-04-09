#! /usr/bin/env python
# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ludwig.constants import EXECUTOR, STRATEGY, MINIMIZE
from ludwig.utils.defaults import default_random_seed
from ludwig.utils.misc import get_from_registry, set_default_values, set_default_value

logger = logging.getLogger(__name__)


class HyperoptStrategy((ABC)):
    def __init__(self, goal: str, parameters: Dict[str, Any]) -> None:
        self.goal = goal  # useful for bayesian stratiegy
        self.parameters = parameters

    @abstractmethod
    def sample(self) -> Dict[str, Any]:
        # Yields a set of parameters names and their values.
        # Define `build_hyperopt_strategy` which would take paramters as inputs
        pass

    @abstractmethod
    def update(
            self,
            sampled_parameters: Dict[str, Any],
            statistics: Dict[str, Any]
    ):
        # Given the results of previous computation, it updates
        # the strategy (not needed for stateless strategies like "grid"
        # and random, but will be needed by bayesian)
        pass


class RandomStrategy(HyperoptStrategy):
    def __init__(
            self,
            goal: str,
            parameters: Dict[str, Any],
            num_samples=10
    ) -> None:
        HyperoptStrategy.__init__(self, goal, parameters)
        self.num_samples = num_samples

    def sample(self) -> Dict[str, Any]:
        # actual implementation ...
        pass

    def update(
            self,
            sampled_parameters: Dict[str, Any],
            statistics: Dict[str, Any]
    ):
        # actual implementation ...
        pass


class GridStrategy(HyperoptStrategy):
    def __init__(self, goal: str, parameters: Dict[str, Any]) -> None:
        HyperoptStrategy.__init__(self, goal, parameters)

    def sample(self) -> Dict[str, Any]:
        # actual implementation ...
        pass

    def update(
            self,
            sampled_parameters: Dict[str, Any],
            statistics: Dict[str, Any]
    ):
        # actual implementation ...
        pass


class HyperoptExecutor((ABC)):
    def __init__(
            self,
            hyperopt_strategy: HyperoptStrategy,
            output_feature: str,
            metric: str,
            split: str
    ) -> None:
        self.hyperopt_strategy = hyperopt_strategy
        self.output_feature = output_feature
        self.metric = metric
        self.split = split

    def get_metric(self, training_results):
        return training_results[self.split][self.output_feature][self.metric]

    def sort_hyperopt_results(self, hyperopt_results):
        return sorted(
            hyperopt_results,
            key=lambda hp_res: hp_res['metric_val'],
            reverse=self.hyperopt_strategy.goal == MINIMIZE
        )

    @abstractmethod
    def execute(
            self,
            model_definition,
            data_df=None,
            data_train_df=None,
            data_validation_df=None,
            data_test_df=None,
            data_csv=None,
            data_train_csv=None,
            data_validation_csv=None,
            data_test_csv=None,
            data_hdf5=None,
            data_train_hdf5=None,
            data_validation_hdf5=None,
            data_test_hdf5=None,
            train_set_metadata_json=None,
            experiment_name="hyperopt",
            model_name="run",
            model_load_path=None,
            model_resume_path=None,
            skip_save_training_description=False,
            skip_save_training_statistics=False,
            skip_save_model=False,
            skip_save_progress=False,
            skip_save_log=False,
            skip_save_processed_input=False,
            skip_save_unprocessed_output=False,
            skip_save_test_predictions=False,
            skip_save_test_statistics=False,
            output_directory="results",
            gpus=None,
            gpu_fraction=1.0,
            use_horovod=False,
            random_seed=default_random_seed,
            debug=False,
            **kwargs
    ):
        pass


class SerialExecutor(HyperoptExecutor):
    def __init__(
            self,
            hyperopt_strategy: HyperoptStrategy,
            output_feature: str,
            measure: str,
            split: str,
            other_params
    ) -> None:
        HyperoptExecutor.__init__(
            self, hyperopt_strategy, output_feature, measure, split
        )
        self.other_params = other_params

    def execute(
            self,
            model_definition,
            data_df=None,
            data_train_df=None,
            data_validation_df=None,
            data_test_df=None,
            data_csv=None,
            data_train_csv=None,
            data_validation_csv=None,
            data_test_csv=None,
            data_hdf5=None,
            data_train_hdf5=None,
            data_validation_hdf5=None,
            data_test_hdf5=None,
            train_set_metadata_json=None,
            experiment_name="hyperopt",
            model_name="run",
            model_load_path=None,
            model_resume_path=None,
            skip_save_training_description=False,
            skip_save_training_statistics=False,
            skip_save_model=False,
            skip_save_progress=False,
            skip_save_log=False,
            skip_save_processed_input=False,
            skip_save_unprocessed_output=False,
            skip_save_test_predictions=False,
            skip_save_test_statistics=False,
            output_directory="results",
            gpus=None,
            gpu_fraction=1.0,
            use_horovod=False,
            random_seed=default_random_seed,
            debug=False,
            **kwargs
    ):
        hyperopt_results = []
        sampled_parameters = self.hyperopt_strategy.sample()

        for parameters in sampled_parameters:
            model_definition = substitute_parameters(
                model_definition, parameters
            )

            # TODO:Train model with Sampled parameters and function params & get `train_stats`.
            # Collect training and validation losses and measures & append it to `results`
            training_results = None
            metric_val = self.get_metric(training_results)

            hyperopt_results.append({
                'parameters': parameters,
                'metric_val': metric_val,
                'training_results': training_results
            })

        hyperopt_results = self.sort_hyperopt_results(hyperopt_results)

        return hyperopt_results


class ParallelExecutor:
    def __init__(self, **kwargs):
        pass

    def __call__(self, **kwargs):
        pass


def get_build_hyperopt_strategy(strategy_type):
    return get_from_registry(
        strategy_type, strategy_registry
    )


def get_build_hyperopt_executor(executor_type):
    return get_from_registry(
        executor_type, executor_registry
    )


strategy_registry = {
    "random": RandomStrategy,
    "grid": GridStrategy
}

executor_registry = {
    "serial": SerialExecutor,
    "parallel": ParallelExecutor
}


def update_hyperopt_params_with_defaults(hyperopt_params):
    set_default_value(hyperopt_params, STRATEGY, {})
    set_default_value(hyperopt_params, EXECUTOR, {})

    set_default_values(
        hyperopt_params[STRATEGY],
        {
            "type": "random",
            "num_samples": 12
        }
    )

    if hyperopt_params[STRATEGY]["type"] == "grid":
        set_default_values(
            hyperopt_params[STRATEGY],
            {
                # Put Grid default values
            },
        )

    set_default_values(
        hyperopt_params[EXECUTOR],
        {
            "type": "serial"
        }
    )

    if hyperopt_params[EXECUTOR]["type"] == "parallel":
        set_default_values(
            hyperopt_params[EXECUTOR],
            {
                "num_workers": 4
            }
        )


def set_values(model_dict, name, parameters_dict):
    if name in parameters_dict:
        params = parameters_dict[name]
        for key, value in params.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    model_dict[key][sub_key] = sub_value
            else:
                model_dict[key] = value


def get_parameters_dict(parameters):
    parameters_dict = {}
    for name, value in parameters.items():
        curr_dict = parameters_dict
        name_list = name.split(".")
        for i, name_elem in enumerate(name_list):
            if i == len(name_list) - 1:
                curr_dict[name_elem] = value
            else:
                name_dict = curr_dict.get(name_elem, {})
                curr_dict[name_elem] = name_dict
                curr_dict = name_dict
    return parameters_dict


def substitute_parameters(model_definition, parameters):
    parameters_dict = get_parameters_dict(parameters)
    for input_feature in model_definition["input_features"]:
        set_values(input_feature, input_feature["name"], parameters_dict)
    for output_feature in model_definition["output_features"]:
        set_values(output_feature, output_feature["name"], parameters_dict)
    set_values(model_definition["combiner"], "combiner", parameters_dict)
    set_values(model_definition["training"], "training", parameters_dict)
    set_values(model_definition["preprocessing"],
               "preprocessing", parameters_dict)
    return model_definition
