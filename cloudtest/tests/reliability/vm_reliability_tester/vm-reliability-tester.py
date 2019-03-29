# -*- coding: utf-8 -*-
"""
Created on Wed Mar 04 14:59:40 2015

@author: Konstantin
"""

import test_executor
import test_setup
import test_measurer
import test_cleanup
import measurements_consolidator
import data_processing
import model_fitter
import model_validator
import os

if __name__ == "__main__":
    print os.getcwd()
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    print os.getcwd()
    test_cleanup.clean()
    test_setup.setup()
    for i in range(10):
        test_executor.run()
        test_measurer.data_collection()
        measurements_consolidator.set_data_point()
        test_cleanup.run()
    data_processing.add_diffs()
    model_fitter.fit_models()
    test_cleanup.clean()
    test_setup.setup()
    for i in range(10):
        test_executor.run()
        test_measurer.data_collection()
        measurements_consolidator.set_data_point()
        test_cleanup.run()
    data_processing.add_diffs()
    model_validator.fit_models()
