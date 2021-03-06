#include <algorithm>
#include <vector>

#include "caffe/layers/euclidean_loss_layer.hpp"
#include "caffe/util/math_functions.hpp"
//#include "caffe/loss_layers.hpp"

namespace caffe {

template <typename Dtype>
void EuclideanLossLayer<Dtype>::LayerSetUp(const vector<Blob<Dtype>*>& bottom,
				const vector<Blob<Dtype>*>& top){
		LossLayer<Dtype>::LayerSetUp(bottom, top);
		EuclideanLossParameter euclid_loss = this->layer_param_.euclideanloss_param();
		is_normalize_     = euclid_loss.is_normalized();
		nc_               = euclid_loss.normalize_choice(); 
		CHECK_GE(nc_, 0) << "normalize_choice can be 0 or 1";
		CHECK_LE(nc_, 1) << "normalize_choice can be 0 or 1"; 
		
		/*
		LOG(INFO) << "Setup Euclidean " << "Normalize: " << is_normalize_ << " nc_: " << nc_;
		if (is_normalize_)
			LOG(INFO) << "normalization is ON";
		else
			LOG(INFO) << "normalization is OFF";
		*/
}


template <typename Dtype>
void EuclideanLossLayer<Dtype>::Reshape(
  const vector<Blob<Dtype>*>& bottom, const vector<Blob<Dtype>*>& top) {
  LossLayer<Dtype>::Reshape(bottom, top);
  CHECK_EQ(bottom[0]->count(1), bottom[1]->count(1))
      << "Inputs must have the same dimension.";
  diff_.ReshapeLike(*bottom[0]);
}

template <typename Dtype>
void EuclideanLossLayer<Dtype>::Forward_cpu(const vector<Blob<Dtype>*>& bottom,
    const vector<Blob<Dtype>*>& top) {
  int count = bottom[0]->count();
  caffe_sub(
      count,
      bottom[0]->cpu_data(),
      bottom[1]->cpu_data(),
      diff_.mutable_cpu_data());
  Dtype dot = caffe_cpu_dot(count, diff_.cpu_data(), diff_.cpu_data());
	if (is_normalize_){
		Dtype nrmlz = caffe_cpu_dot(count, bottom[nc_]->cpu_data(), bottom[nc_]->cpu_data());
		if (nrmlz > 0){
			dot = dot / nrmlz;
		}
	}
  Dtype loss = dot / bottom[0]->num() / Dtype(2);
  top[0]->mutable_cpu_data()[0] = loss;
}

template <typename Dtype>
void EuclideanLossLayer<Dtype>::Backward_cpu(const vector<Blob<Dtype>*>& top,
    const vector<bool>& propagate_down, const vector<Blob<Dtype>*>& bottom) {
  for (int i = 0; i < 2; ++i) {
    if (propagate_down[i]) {
      const Dtype sign = (i == 0) ? 1 : -1;
      const Dtype alpha = sign * top[0]->cpu_diff()[0] / (bottom)[i]->num();
			Dtype nrmlz       = 1.0;      
			int count = (bottom)[0]->count();
			if (is_normalize_){
				nrmlz = caffe_cpu_dot(count, (bottom)[nc_]->cpu_data(), (bottom)[nc_]->cpu_data());
				if (nrmlz>0){
					caffe_scal(count, Dtype(1)/nrmlz, diff_.mutable_cpu_data());
				}
			}

			caffe_cpu_axpby(
          (bottom)[i]->count(),              // count
          alpha,                              // alpha
          diff_.cpu_data(),                    // a
          Dtype(0),                           // beta
          bottom[i]->mutable_cpu_diff());  // b
    }
  }
}

#ifdef CPU_ONLY
STUB_GPU(EuclideanLossLayer);
#endif

INSTANTIATE_CLASS(EuclideanLossLayer);
REGISTER_LAYER_CLASS(EuclideanLoss);

}  // namespace caffe
