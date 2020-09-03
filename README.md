# Z score

Calculate z-scores of anthropometric measurements based on WHO

## Installation

pip install zscore

## Usage

from cgmzscore import Calculator
calculator=Calculator()


v=calculator.zScore_wfa(weight="7.853",age_in_months='16',sex='M',height='73')


## Different function of calculator

zScore_wfa
zScore_wfl/zScore_wfh
zScore_lhfa

## TODO

SAM/MAM/Classifier


