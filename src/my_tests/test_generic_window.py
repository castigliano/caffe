import numpy as np
import other_utils as ou
import matplotlib.pyplot as plt
import pdb
import caffe
import os
import scipy.misc as scm
import time

#sFile =  "/data0/pulkitag/kitti/window-files/test_mxDiff-7_pose-sigMotion_nrmlz-zScoreScaleSeperate_imSz256_concat-fc6_nTe-10000.txt"
#rootFolder = "/data1/pulkitag/data_sets/kitti/odometry/dataset/sequences/imSz256/" 
#rootFolder = "/data0/pulkitag/data_sets/kitti/odometry/dataset/sequences/asJpg/" 

#Streetview
#sFile =  "/data0/pulkitag/data_sets/streetview/exp/window-files/train_pose-euler-mxRot45_geo-dc-v1_crpSz192_nTr-1.00e+06.txt"
sFile =  "/data0/pulkitag/data_sets/streetview/exp/window-files/test_ptch-wngtv-posFrac0.5_spDist100_spVer-v1_geodc-v2_geo-dc-v2_crpSz192_nTe-1.00e+04_rawImSz256.txt"
rootFolder = "/data0/pulkitag/data_sets/streetview/proc/resize-im/im256/"

def get_protofile(isGray=False, dataset='kitti'):
	#protoDir = '/home/ubuntu/caffe-v2-3/src/my_tests/' 
	protoDir   = '/work4/pulkitag-code/pkgs/caffe-v2-3/src/my_tests/'
	if isGray:
		protoFile = os.path.join(protoDir, 'generic_window_gray.prototxt')
	else:
		if dataset == 'sf':
			protoFile   = os.path.join(protoDir, 'generic_window_sf.prototxt')
		elif dataset == 'kitti':
			protoFile   = os.path.join(protoDir, 'generic_window.prototxt')
		elif dataset == 'streetview':
			#protoFile   = os.path.join(protoDir, 'generic_window_streetview.prototxt')
			print ('USING PYTHON WINDOW DATA LAYER')
			protoFile   = os.path.join(protoDir, 'proto_files', 
												'python_window_layer.prototxt')
			
	return protoFile


def read_window_file(fName=sFile):
	fid = open(fName,'r')
	lines = fid.readlines()
	fid.close()
	
	headerL = lines[0]
	numEx   = int(lines[1].split()[0])
	numIm   = int(lines[2].split()[0])
	labelSz = int(lines[3].split()[0])
	lines   = lines[4:]	
	
	imNames = {}
	bbox    = {}
	labels  = np.zeros((numEx, labelSz)).astype('float')
	for i in range(numIm):
		keyName = 'im%d' % (i+1)
		imNames[keyName] = []
		bbox[keyName]    = []

	readFlag = True
	lCount   = 0
	imCount  = 0
	while readFlag:
		l = lines[lCount]
		assert imCount==int(l.split()[1])
		imStr   = []
		for i in range(numIm):
			keyName = 'im%d' % (i+1)
			lCount += 1
			data   = lines[lCount].split()
			#Image Name
			imNames[keyName].append(data[0])
			#bbox coords
			box = [int(d) for d in data[4:]]
			bbox[keyName].append(box)	
		
		lCount += 1
		data   = lines[lCount].split()
		for j in range(labelSz):
			labels[imCount,j] = float(data[j])
		imCount += 1
		lCount  += 1
		if imCount == numEx:
			readFlag = False
	return imNames, bbox, labels


def plot_pairs(fig, im1, im2, titleStr='', figTitle=''):
	plt.figure(fig.number)
	ax1 = plt.subplot(1,2,1)
	ax2 = plt.subplot(1,2,2)
	ax1.imshow(im1.astype(np.uint8))
	ax1.axis('off')
	ax2.imshow(im2.astype(np.uint8))
	ax2.axis('off')
	plt.title(titleStr)
	fig.suptitle(figTitle)
	plt.show()

def compare_windows(isGray=False, isSave=False, svIdx=None, svPath=None, dataset='streetview'):
	figGt = plt.figure()  #Ground-Truth
	figDt = plt.figure()	#Data
	plt.ion()
	plt.set_cmap(plt.cm.gray)
	
	#Get ground truth data.
	imNamesGt, bboxGt, labelsGt = read_window_file()
	N = labelsGt.shape[0]	
	N = 100

	#Crop Ground Truth or not
	isCropGt = False

	#Setup the network. 
	protoFile = get_protofile(isGray, dataset=dataset)
	net       = caffe.Net(protoFile, caffe.TRAIN)
	imCount = 0
	cropPrms = {}
	cropPrms['cropType'] = 'contPad'
	cropPrms['imSz']     = 227
	cropPrms['contPad']  = 0
	svCount = 0
	for i in range(N):
		allDat  = net.forward(['data','label'])
		imData  = allDat['data']
		lblDat  = allDat['label']
		batchSz = imData.shape[0]
		#time.sleep(2)
		for b in range(batchSz):
			#Plot network data. 
			if isGray:
				im1 = imData[b,0:1].transpose((1,2,0)).squeeze()
				im2 = imData[b,1:].transpose((1,2,0)).squeeze()
			else:
				im1 = imData[b,0:3].transpose((1,2,0))
				im2 = imData[b,3:6].transpose((1,2,0))
				im1 = im1[:,:,[2,1,0]]
				im2 = im2[:,:,[2,1,0]]

			lb  = lblDat[b].squeeze()
			if dataset in ['kitti', 'sf']:
				lbStr = 'az: %f, el: %f, cl: %f' % (lb[0],lb[1],lb[2])
			else:
				#lbStr = 'az: %f, el: %f' % (lb[0],lb[1])
				print lb
				lbStr = 'isMatch: %f'  % lb
					
		
			if isSave:
				if imCount in svIdx:
					imN1 = svPath % (svCount,1)
					imN2 = svPath % (svCount,2)
					scm.imsave(imN1, im1)
					scm.imsave(imN2, im2)
					svCount += 1
					if svCount == len(svIdx):
						print 'Saved all images: %d' % svCount
						return
			else:
				plot_pairs(figDt, im1, im2, lbStr, 'Layer Output') 
				#Plot the gt data
				imName1 = os.path.join(rootFolder, imNamesGt['im1'][imCount])
				imName2 = os.path.join(rootFolder, imNamesGt['im2'][imCount])
				print (imName1)
				if isCropGt:
					im1   = ou.read_crop_im(imName1, bboxGt['im1'][imCount], **cropPrms)
					im2   = ou.read_crop_im(imName2, bboxGt['im2'][imCount], **cropPrms)
				else:
					im1   = plt.imread(imName1)
					im2   = plt.imread(imName2)
					
				lb    = labelsGt[imCount]
				if dataset in ['kitti', 'sf']:
					lbStr = 'az: %f, el: %f, cl: %f' % (lb[0],lb[1],lb[2])
				else:
					#lbStr = 'az: %f, el: %f' % (lb[0],lb[1])
					lbStr = 'isMatch: %f'  % lb[0]
				plot_pairs(figGt, im1, im2, lbStr, 'Ground Truth')
				print imCount
				ip = raw_input()
				if ip=='q':
					return

			imCount += 1
			if imCount==N:
				imCount = 0

def save_pairs():
	figGt = plt.figure()  #Ground-Truth
	ax    = plt.subplot(1,1,1)
	plt.ion()

	cropPrms = {}
	cropPrms['cropType'] = 'contPad'
	cropPrms['imSz']     = 227
	cropPrms['contPad']  = 0

	saveDir = '/data1/pulkitag/data_sets/pascal_3d/my/debug/'
	saveDir1 = os.path.join(saveDir, 'im1')
	saveDir2 = os.path.join(saveDir, 'im2')
	imNamesGt, bboxGt, labelsGt = read_window_file()
	for imCount in range(100):
		 	imName1 = os.path.join(rootFolder, imNamesGt['im1'][imCount])
			imName2 = os.path.join(rootFolder, imNamesGt['im2'][imCount])
			im1   = ou.read_crop_im(imName1, bboxGt['im1'][imCount], **cropPrms)
			im2   = ou.read_crop_im(imName2, bboxGt['im2'][imCount], **cropPrms)
			bName1 = os.path.basename(imNamesGt['im1'][imCount]).split('.')[0]
			bName2 = os.path.basename(imNamesGt['im2'][imCount]).split('.')[0]
			sName1 = os.path.join(saveDir1, 'im%d_%s.png' % (imCount, bName1))
			sName2 = os.path.join(saveDir2, 'im%d_%s.png' % (imCount, bName2))
			ax.imshow(im1)
			plt.savefig(sName1)
			ax.imshow(im2)
			plt.savefig(sName2)	


if __name__ == '__main__':
	compare_windows()	
