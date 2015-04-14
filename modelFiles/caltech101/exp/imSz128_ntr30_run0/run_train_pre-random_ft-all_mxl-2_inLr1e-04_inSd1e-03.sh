#!/usr/bin/env sh 
 
TOOLS=/work4/pulkitag-code/pkgs/caffe-v2-2/build/tools 
 
GLOG_logtostderr=1 $TOOLS/caffe train	 --solver=/work4/pulkitag-code/pkgs/caffe-v2-2/modelFiles/caltech101/exp/imSz128_ntr30_run0/solver_pre-random_ft-all_mxl-2_inLr1e-04_inSd1e-03.prototxt	 -gpu 0	 2>&1 | tee /work4/pulkitag-code/pkgs/caffe-v2-2/modelFiles/caltech101/exp/imSz128_ntr30_run0/log_train_pre-random_ft-all_mxl-2_inLr1e-04_inSd1e-03.txt 
