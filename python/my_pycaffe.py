import numpy as np
import h5py
import caffe
import pdb
import matplotlib.pyplot as plt
import os
from six import string_types

class layerSz:
	def __init__(self, stride, filterSz):
		self.imSzPrev = [] #We will assume square images for now
		self.stride   = stride #Stride with which filters are applied
		self.filterSz = filterSz #Size of filters. 
		self.stridePixPrev = [] #Stride in image pixels of the filters in the previous layers.
		self.pixelSzPrev   = [] #Size of the filters in the previous layers in the image space
		#To be computed
		self.pixelSz   = [] #the receptive field size of the filter in the original image.
		self.stridePix = [] #Stride of units in the image pixel domain.

	def prev_prms(self, prevLayer):
		self.set_prev_prms(prevLayer.stridePix, prevLayer.pixelSz)

	def set_prev_prms(self, stridePixPrev, pixelSzPrev):
		self.stridePixPrev = stridePixPrev
		self.pixelSzPrev   = pixelSzPrev

	def compute(self):
		self.pixelSz   = self.pixelSzPrev + (self.filterSz-1)*self.stridePixPrev	  
		self.stridePix = self.stride * self.stridePixPrev


def calculate_size():
	'''
		Calculate the receptive field size and the stride of the Alex-Net
	'''
	conv1 = layerSz(4,11)
	conv1.set_prev_prms(1,1)
	conv1.compute()
	pool1 = layerSz(2,3)
	pool1.prev_prms(conv1)
	pool1.compute()

	conv2 = layerSz(1,5)
	conv2.prev_prms(pool1)
	conv2.compute()
	pool2 = layerSz(2,3)
	pool2.prev_prms(conv2)
	pool2.compute()

	conv3 = layerSz(1,3)
	conv3.prev_prms(pool2)
	conv3.compute()

	conv4 = layerSz(1,3)
	conv4.prev_prms(conv3)
	conv4.compute()

	conv5 = layerSz(1,3)
	conv5.prev_prms(conv4)
	conv5.compute()
	pool5 = layerSz(2,3)
	pool5.prev_prms(conv5)
	pool5.compute()

	print 'Pool1: Receptive: %d, Stride: %d ' % (pool1.pixelSz, pool1.stridePix)	
	print 'Pool2: Receptive: %d, Stride: %d ' % (pool2.pixelSz, pool2.stridePix)	
	print 'Conv3: Receptive: %d, Stride: %d ' % (conv3.pixelSz, conv3.stridePix)	
	print 'Conv4: Receptive: %d, Stride: %d ' % (conv4.pixelSz, conv4.stridePix)	
	print 'Pool5: Receptive: %d, Stride: %d ' % (pool5.pixelSz, pool5.stridePix)	
	

def find_layer(lines):
	layerName = []
	for l in lines:
		if 'type' in l:
			_,layerName = l.split()
			return layerName


def netdef2siamese(defFile, outFile):
	outFid = open(outFile,'w')
	stream1, stream2 = [],[]
	with open(defFile,'r') as fid:
		lines     = fid.readlines()
		layerFlag = 0
		for (i,l) in enumerate(lines):
			#Indicates if the line has been added or not
			addFlag = False
			if 'layers' in l:
				layerName = find_layer(lines[i:])
				print layerName
				#Go in the state that this a useful layer to model. 
				if layerName in ['CONVOLUTION', 'INNER_PRODUCT']:
					layerFlag = 1
			
			#Manage the top, bottom and name for the two streams in case of a layer with params. 
			if 'bottom' in l or 'top' in l or 'name' in l:
				stream1.append(l)
				pre, suf = l.split()
				suf  = suf[0:-1] + '_p"'
				newL = pre + ' ' + suf + '\n'
				stream2.append(newL)
				addFlag = True

			#Store the name of the parameters	
			if layerFlag > 0 and 'name' in l:
				_,paramName = l.split()
				paramName   = paramName[1:-1]
			
			#Dont want to overcount '{' multiple times for the line 'layers {'	
			if (layerFlag > 0) and ('{' in l) and ('layers' not in l):
				layerFlag += 1	
			
			if '}' in l:
				print layerFlag
				layerFlag = layerFlag - 1
				#Before the ending the layer definition inlucde the param
				if layerFlag == 0:
					stream1.append('\t param: "%s" \n' % (paramName + '_w'))
					stream1.append('\t param: "%s" \n' % (paramName + '_b'))
					stream2.append('\t param: "%s" \n' % (paramName + '_w'))
					stream2.append('\t param: "%s" \n' % (paramName + '_b'))
						
			if not addFlag:
				stream1.append(l)
				stream2.append(l)

	#Write the first stream of the siamese net. 
	for l in stream1:
		outFid.write('%s' % l)

	#Write the second stream of the siamese net. 
	skipFlag  = False
	layerFlag = 0
	for (i,l) in enumerate(stream2):
		if 'layers' in l:
			layerName = find_layer(stream2[i:])
			#Skip writing the data layers in stream 2
			if layerName in ['DATA']:
				skipFlag  = True
				layerFlag = 1
		
		#Dont want to overcount '{' multiple times for the line 'layers {'	
		if layerFlag > 1 and '{' in l:
			layerFlag += 1	

		#Write to the out File	
		if not skipFlag:
			outFid.write('%s' % l)	
	
		if '}' in l:
			layerFlag = layerFlag - 1
			if layerFlag == 0:
				skipFlag = False
	outFid.close()


def get_model_mean_file(netName='vgg'):
	'''
		Returns 
			the model file - the .caffemodel with the weights
			the mean file of the imagenet data
	'''
	modelDir = '/data1/pulkitag/caffe_models/'
	bvlcDir  = modelDir + 'bvlc_reference/'
	if netName   == 'alex':
		modelFile  = modelDir + 'caffe_imagenet_train_iter_310000'
		imMeanFile = modelDir + 'ilsvrc2012_mean.binaryproto'
	if netName == 'bvlcAlexNet':
		modelFile  = bvlcDir + 'bvlc_reference_caffenet.caffemodel'
		imMeanFile = bvlcDir + 'imagenet_mean.binaryproto'  
	elif netName == 'vgg':
		modelFile    = '/data1/pulkitag/caffe_models/VGG_ILSVRC_19_layers.caffemodel'
		imMeanFile = '/data1/pulkitag/caffe_models/ilsvrc2012_mean.binaryproto'
	elif netName  == 'lenet':
		modelFile  = '/data1/pulkitag/mnist/snapshots/lenet_iter_20000.caffemodel'
		imMeanFile = None
	else:
		print 'netName not recognized'
		return

	return modelFile, imMeanFile
	

def get_layer_def_files(netName='vgg', layerName='pool4'):
	'''
		Returns
			the architecture definition file of the network uptil layer layerName
	'''
	modelDir = '/data1/pulkitag/caffe_models/'
	bvlcDir  = modelDir + 'bvlc_reference/'
	if netName=='vgg':
		defFile = modelDir + 'layer_def_files/vgg_19_%s.prototxt' % layerName
	elif netName == 'bvlcAlexNet':
		defFile = bvlcDir + 'caffenet_deploy_%s.prototxt' % layerName
	else:
		print 'Cannont get files for networks other than VGG'
	return defFile	


def get_input_blob_shape(defFile):
	'''
		Get the shape of input blob from the defFile
	'''
	blobShape = []
	with open(defFile,'r') as f:
		lines  = f.readlines()
		ipMode = False
		for l in lines:
			if 'input:' in l:
				ipMode = True
			if ipMode and 'input_dim:' in l:
				ips = l.split()
				blobShape.append(int(ips[1]))
	return blobShape

				
def read_mean(protoFileName):
	'''
		Reads mean from the protoFile
	'''
	with open(protoFileName,'r') as fid:
		ss = fid.read()
		vec = caffe.io.caffe_pb2.BlobProto()
		vec.ParseFromString(ss)
		mn = caffe.io.blobproto_to_array(vec)
	mn = np.squeeze(mn)
	return mn


class MyNet:
	def __init__(self, defFile, modelFile=None, isGPU=True, testMode=True, deviceId=None):
		self.defFile_   = defFile
		self.modelFile_ = modelFile
		self.testMode_  = testMode
		self.setup_network()
		self.set_mode(isGPU, deviceId=deviceId)
		self.transformer = {}


	def setup_network(self):
		if self.testMode_:
			if not self.modelFile_ is None:
				self.net = caffe.Net(self.defFile_, self.modelFile_, caffe.TEST)
			else:
				self.net = caffe.Net(self.defFile_, caffe.TEST)
		else:
			if not self.modelFile_ is None:
				self.net = caffe.Net(self.defFile_, self.modelFile_, caffe.TRAIN)
			else:
				self.net = caffe.Net(self.defFile_, caffe.TRAIN)
		self.batchSz   = self.get_batchsz()


	def set_mode(self, isGPU=True, deviceId=None):
		if isGPU:
			caffe.set_mode_gpu()
		else:
			caffe.set_mode_cpu()
		if deviceId is not None:
			caffe.set_device(deviceId)
	
	def get_batchsz(self):
		if len(self.net.inputs) > 0:
			return self.net.blobs[self.net.inputs[0]].num
		else:
			return None

	def get_blob_shape(self, blobName):
		assert blobName in self.net.blobs.keys(), 'Blob Name is not present in the net'
		blob = self.net.blobs[blobName]
		return blob.num, blob.channels, blob.height, blob.width

	
	def set_preprocess(self, ipName='data',chSwap=(2,1,0), meanDat=None, imageDims=None, isBlobFormat=False, rawScale=None):
		'''
			isBlobFormat: if the images are already coming in blobFormat or not. 
			ipName    : the blob for which the pre-processing parameters need to be set. 
			meanDat   : the mean which needs to subtracted
			imageDims : the size of the images as H * W * K where K is the number of channels
		'''
		self.transformer[ipName] = caffe.io.Transformer({ipName: self.net.blobs[ipName].data.shape})
		#Note blobFormat will be so used that finally the image will need to be flipped. 
		self.transformer[ipName].set_transpose(ipName, (2,0,1))	
	
		if chSwap is not None:
			#Required for eg RGB to BGR conversion.
			self.transformer[ipName].set_channel_swap(ipName, chSwap)
	
		if rawScale is not None:
			self.transformer[ipName].set_raw_scale(ipName, rawScale)
	
		#Crop Dimensions
		ipDims            = np.array(self.net.blobs[ipName].data.shape)
		self.cropDims     = ipDims[2:]
		self.isBlobFormat = isBlobFormat 
		if imageDims is None:
			imageDims = np.array([ipDims[2], ipDims[3], ipDims[1]])
		else:
			assert len(imageDims)==3
			imageDims = np.array([imageDims[0], imageDims[1], imageDims[2]])
		self.imageDims = imageDims
		self.get_crop_dims()		
		
		#Mean Subtraction
		if not meanDat is None:
			if isinstance(meanDat, string_types):
				meanDat = read_mean(meanDat)
			_,h,w = meanDat.shape
			assert self.imageDims[0]==h and self.imageDims[1]==w, 'imageDims must match mean Image size, (h,w), (imH, imW): (%d, %d), (%d,%d)' % (h,w,self.imageDims[0],self.imageDims[1])
			meanDat  = meanDat[:, self.crop[0]:self.crop[2], self.crop[1]:self.crop[3]] 
			self.transformer[ipName].set_mean(ipName, meanDat)
	
	
	def get_crop_dims(self):
		# Take center crop.
		center = np.array(self.imageDims[0:2]) / 2.0
		crop = np.tile(center, (1, 2))[0] + np.concatenate([
				-self.cropDims / 2.0,
				self.cropDims / 2.0
		])
		self.crop = crop


	def resize_batch(self, ims):
		if ims.shape[0] > self.batchSz:
			assert False, "More input images than the batch sz"
		if ims.shape[0] == self.batchSz:
			return ims
		print "Adding Zero Images to fix the batch, Size: %d" % ims.shape[0]
		N,ch,h,w = ims.shape
		imZ      = np.zeros((self.batchSz - N, ch, h, w))
		ims      = np.concatenate((ims, imZ))
		return ims 
		

	def preprocess_batch(self, ims, ipName='data'):	
		'''
			ims: iterator over H * W * K sized images (K - number of channels) or K * H * W format. 
		'''
		#The image necessary needs to be float - otherwise caffe.io.resize fucks up.
		ims = ims.astype(np.float32)
		if np.max(ims)<=1.0:
			print "There maybe issues with image scaling. The maximum pixel value is 1.0 and not 255.0"
	
		assert ipName in self.transformer.keys()

		im_ = np.zeros((len(ims), 
            self.imageDims[0], self.imageDims[1], self.imageDims[2]),
            dtype=np.float32)
		#Resize the images
		for ix, in_ in enumerate(ims):
			if self.isBlobFormat:
				im_[ix] = caffe.io.resize_image(in_.transpose((1,2,0)), self.imageDims[0:2])
			else:
				print in_.shape
				im_[ix] = caffe.io.resize_image(in_, self.imageDims[0:2])

		#Required cropping
		im_ = im_[:,self.crop[0]:self.crop[2], self.crop[1]:self.crop[3],:]	
		
		#Applying the preprocessing
		caffe_in = np.zeros(np.array(im_.shape)[[0,3,1,2]], dtype=np.float32)
		for ix, in_ in enumerate(im_):
			caffe_in[ix] = self.transformer[ipName].preprocess(ipName, in_)

		#Resize the batch appropriately
		caffe_in = self.resize_batch(caffe_in)
		return caffe_in

	
	def deprocess_batch(self, caffeIn, ipName='data'):	
		'''
			ims: iterator over H * W * K sized images (K - number of channels)
		'''
		#Applying the deprocessing
		im_ = np.zeros(np.array(caffeIn.shape)[[0,2,3,1]], dtype=np.float32)
		for ix, in_ in enumerate(caffeIn):
			im_[ix] = self.transformer[ipName].deprocess(ipName, in_)

		ims = np.zeros((len(im_), 
            self.imageDims[0], self.imageDims[1], im_[0].shape[2]),
            dtype=np.float32)
		#Resize the images
		for ix, in_ in enumerate(im_):
			ims[ix] = caffe.io.resize_image(in_, self.imageDims)

		return ims


	def vis_weights(self, blobName, blobNum=0): 
		assert blobName in self.net.blobs, 'BlobName not found'
		dat  = self.net.params[blobName][blobNum].data
		vis_square(dat.transpose(0,2,3,1))	


def vis_square(data, padsize=1, padval=0):
	'''
		data is numFitlers * height * width or numFilters * height * width * channels
	'''

	data -= data.min()
	data /= data.max()

	# force the number of filters to be square
	n = int(np.ceil(np.sqrt(data.shape[0])))
	padding = ((0, n ** 2 - data.shape[0]), (0, padsize), (0, padsize)) + ((0, 0),) * (data.ndim - 3)
	data = np.pad(data, padding, mode='constant', constant_values=(padval, padval))

	# tile the filters into an image
	data = data.reshape((n, n) + data.shape[1:]).transpose((0, 2, 1, 3) + tuple(range(4, data.ndim + 1)))
	data = data.reshape((n * data.shape[1], n * data.shape[3]) + data.shape[4:])

	plt.imshow(data)



def setup_prototypical_network(netName='vgg', layerName='pool4'):
	'''
		Sets up a network in a configuration in which I commonly use it. 
	'''
	modelFile, meanFile = get_model_mean_file(netName)
	defFile             = get_layer_def_files(netName, layerName=layerName)
	meanDat             = read_mean(meanFile)
	net                 = MyNet(defFile, modelFile)
	net.set_preprocess(ipName='data', meanDat=meanDat, imageDims=(256,256,3))
	return net	


'''
def get_features(net, im, layerName=None, ipLayerName='data'):
	dataBlob = net.blobs['data']
	batchSz  = dataBlob.num
	assert im.ndim == 4
	N,nc,h,w = im.shape
	assert h == dataBlob.height and w==dataBlob.width

	if not layerName==None:
		assert layerName in net.blobs.keys()
		layerName = [layerName]
		outName   = layerName[0]	
	else:
		outName   = net.outputs[0]
		layerName = []
	
	print layerName
	imBatch = np.zeros((batchSz,nc,h,w))
	outFeats = {}
	outBlob  = net.blobs[outName]
	outFeats = np.zeros((N, outBlob.channels, outBlob.height, outBlob.width))

	for i in range(0,N,batchSz):
		st = i
		en = min(N, st + batchSz)
		l  = en - st
		imBatch[0:l,:,:,:] = np.copy(im[st:en])
		dataLayer = {ipLayerName:imBatch}
		feats = net.forward(blobs=layerName, start=None, end=None, **dataLayer)		 
		outFeats[st:en] = feats[outName][0:l]

	return outFeats

'''


def compute_error(gtLabels, prLabels, errType='classify'):
	N, lblSz = gtLabels.shape
	res = []
	assert prLabels.shape[0] == N and prLabels.shape[1] == lblSz
	if errType == 'classify':
		assert lblSz == 1
		cls     = np.unique(gtLabels)
		cls     = np.sort(cls)
		nCl     = cls.shape[0]
		confMat = np.zeros((nCl, nCl)) 
		for i in range(nCl):
			for j in range(nCl):
				confMat[i,j] = float(np.sum(np.bitwise_and((gtLabels == cls[i]),(prLabels == cls[j]))))/(np.sum(gtLabels == cls[i]))
		res = confMat
	else:
		print "Error type not recognized"
		raise
	return res	


def feats_2_labels(feats, lblType, maskLastLabel=False):
	#feats are assumed to be numEx * featDims
	labels = []
	if lblType in ['uniform20', 'kmedoids30_20']:
		r,c = feats.shape
		if maskLastLabel:
			feats = feats[0:r,0:c-1]
		labels = np.argmax(feats, axis=1)
		labels = labels.reshape((r,1))
	else:
		print "UNrecognized lblType"
		raise
	return labels


def save_images(ims, gtLb, pdLb, svFileStr, stCount=0, isSiamese=False):
	'''
		Saves the images
		ims: N * nCh * H * W 
		gtLb: Ground Truth Label
		pdLb: Predicted Label
		svFileStr: Path should contain (%s, %d) - which will be filled in by correct/incorrect and count
	'''
	N = ims.shape[0]
	ims = ims.transpose((0,2,3,1))
	fig = plt.figure()
	for i in range(N):
		im  = ims[i]
		plt.title('Gt-Label: %d, Predicted-Label: %d' %(gtLb[i], pdLb[i]))
		gl, pl = gtLb[i], pdLb[i]
		if gl==pl:
			fStr = 'correct'
		else:
			fStr = 'mistake'
		if isSiamese:
			im1  = im[:,:,0:3]
			im2  = im[:,:,3:]
			im1  = im1[:,:,[2,1,0]]
			im2  = im2[:,:,[2,1,0]]
			plt.subplot(1,2,1)
			plt.imshow(im1)
			plt.subplot(1,2,2)
			plt.imshow(im2)
			fName = svFileStr % (fStr, i + stCount)
			if not os.path.exists(os.path.dirname(fName)):
				os.makedirs(os.path.dirname(fName))
			print fName
			plt.savefig(fName)
		

def test_network_siamese_h5(imH5File=[], lbH5File=[], netFile=[], defFile=[], imSz=128, cropSz=112, nCh=3, outLblSz=1, meanFile=[], ipLayerName='data', lblType='uniform20',outFeatSz=20, maskLastLabel=False, db=None, svImg=False, svImFileStr=None, deviceId=None):
	'''
		defFile: Architecture prototxt
		netFile : The model weights
		maskLastLabel: In some cases it is we may need to compute the error bt ignoring the last label
									 for example in det - where the last class might be the backgroud class
		db: instead of h5File, provide a dbReader 
	'''
	isBlobFormat = True
	if db is None:
		isBlobFormat = False
		print imH5File, lbH5File
		imFid = h5py.File(imH5File,'r')
		lbFid = h5py.File(lbH5File,'r')
		ims1 = imFid['images1/']
		ims2 = imFid['images2/']
		lbls = lbFid['labels/']
		
		#Get Sizes
		imSzSq = imSz * imSz
		assert(ims1.shape[0] % imSzSq == 0 and ims2.shape[0] % imSzSq ==0)
		N     = ims1.shape[0]/(imSzSq * nCh)
		assert(lbls.shape[0] % N == 0)
		lblSz = outLblSz

	#Get the mean
	imMean = []
	if not meanFile == []:
		imMean = read_mean(meanFile)	

	#Initialize network
	net  = MyNet(defFile, netFile, deviceId=deviceId)
	net.set_preprocess(chSwap=None, meanDat=imMean,imageDims=(imSz, imSz, 2*nCh), isBlobFormat=isBlobFormat, ipName='data')
	
	#Initialize variables
	batchSz  = net.get_batchsz()
	ims      = np.zeros((batchSz, 2 * nCh, imSz, imSz))
	count    = 0
	imCount  = 0

	if db is None:	
		labels   = np.zeros((N, lblSz))
		gtLabels = np.zeros((N, lblSz)) 
		#Loop through the images
		for i in np.arange(0,N,batchSz):
			st = i * nCh * imSzSq 
			en = min(N, i + batchSz) * nCh * imSzSq
			numIm = min(N, i + batchSz) - i
			ims[0:batchSz] = 0
			ims[0:numIm,0:nCh,:,:] = ims1[st:en].reshape((numIm,nCh,imSz,imSz))
			ims[0:numIm,nCh:2*nCh,:,:] = ims2[st:en].reshape((numIm,nCh,imSz,imSz))
			imsPrep   = prepare_image(ims, cropSz, imMean)  
			predFeat  = get_features(net, imsPrep, ipLayerName=ipLayerName)
			predFeat  = predFeat[0:numIm]
			print numIm
			try:
				labels[i : i + numIm, :]    = feats_2_labels(predFeat.reshape((numIm,outFeatSz)), lblType, maskLastLabel=maskLastLabel)[0:numIm]
				gtLabels[i : i + numIm, : ] = (lbls[i * lblSz : (i+numIm) * lblSz]).reshape(numIm, lblSz) 
			except ValueError:
				print "Value Error found"
				pdb.set_trace()
	else:
		labels, gtLabels = [], []
		runFlag = True
		while runFlag:
			count = count + 1
			print "Processing Batch: ", count
			dat, lbl = db.read_batch(batchSz)
			N        = dat.shape[0]
			print N
			if N < batchSz:
				runFlag = False
			batchDat  = net.preprocess_batch(dat, ipName='data')
			dataLayer = {}
			dataLayer[ipLayerName] = batchDat
			feats     = net.net.forward(**dataLayer)
			feats     = feats[feats.keys()[0]][0:N]	
			gtLabels.append(lbl)	
			predLabels = feats_2_labels(feats.reshape((N,outFeatSz)), lblType)
			labels.append(predLabels)
			if svImg:
				save_images(dat, lbl, predLabels, svImFileStr, stCount=imCount, isSiamese=True)
			imCount = imCount + N
		labels   = np.concatenate(labels)
		gtLabels = np.concatenate(gtLabels) 
		
	confMat = compute_error(gtLabels, labels, 'classify')
	return confMat, labels, gtLabels	


def read_mean_txt(fileName):
	with open(fileName,'r') as f:
		l = f.readlines()
		mn = [float(i) for i in l]
		mn = np.array(mn)
	return mn
