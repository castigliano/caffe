import scipy.io as sio
import numpy as np
from   scipy import linalg as linalg
import sys, os
import pdb
import math

def get_rot_angle(view1, view2):
	viewDiff = linalg.logm(np.dot(view2, np.transpose(view1)))
	viewDiff = linalg.norm(viewDiff, ord='fro')
	angle    = viewDiff/np.sqrt(2)
	return angle


def get_cluster_assignments(x, centers):
	N       = x.shape[0]
	nCl     = centers.shape[0]	
	distMat = np.inf * np.ones((nCl,N))
	for c in range(nCl):
		for i in range(N):
			distMat[c,i] = get_rot_angle(centers[c], centers[i])
	
	assgn    = np.argmin(distMat, axis=0)
	minDist  = np.amin(distMat, axis=0)
	meanDist = np.mean(minDist) 
	assert all(minDist.flatten()>0)
	return assgn, meanDist
 

def karcher_mean(x):
	'''
	Determined the Karcher mean of rotations
	Implementation from Algorithm 1, Rotation Averaging, Hartley et al, IJCV 2013
	'''
	R = x[0]
	N = x.shape[0]
	normDeltaR = np.inf

	while True:
		#Estimate the delta rotation between the current center and all points
		deltaR  = np.zeros((3,3))
		oldNorm = normDeltaR
		for i in range(N):
			deltaR = linalg.logm(np.dot(np.transpose(R),x[i]))
		deltaR     = deltaR / N
		normDeltaR = linalg.norm(deltaR, ord='fro')/np.sqrt(2)

		if oldNorm - normDeltaR < tol:
			break
	
		R = np.dot(R, deltaR) 
				
	return R
	

def estimate_clusters(x, assgn, nCl):
	clusters = np.zeros((nCl,3,3))
	for c in range(nCl):
		pointSet    = x[assgn==c]
		clusters[c] = karcher_mean(pointSet) 	

	return clusters	
	

def cluster_rotmats(x,nCl=2,tol=0.01):
	'''
	x  : numMats * 3 * 3
	nCl: number of clusters
	tol: tolerance when to stop, it is basically if the reduction in mean error goes below this point 
	'''
	assert x.shape[1]==x.shape[2]==3
	N  = x.shape[0]

	#Randomly chose some points as initial cluster centers
	perm        = np.random.permutation(N)
	centers     = x[perm[0:N]] 
	assgn, dist = get_cluster_assignment(x, centers)	
	print "Initial Mean Distance is: %f" % dist

	itr = 0
	clusterFlag = True
	while clusterFlag:
		itr        += 1
		prevAssgn  = np.copy(assgn)
		prevDist   = dist
		#Find the new centers
		centers    = estimate_clusters(x, assgn, nCl)
		#Find the new assgn
		assgn,dist = get_cluster_assignment(x, centers)

		print "iteration: %d, mean distance: %f" % (itr,dist)

		if prevDist - dist < tol:
			print "Desired tolerance achieved"
			clusterFlag = False

		if all(assgn==prevAssgn):
			print "Assignments didnot change in this iteration, hence converged"

	return assgn, centers	 	


def axis_to_skewsym(v):
	'''
		Converts an axis into a skew symmetric matrix format. 
	'''
	v = v/np.linalg.norm(v)
	vHat = np.zeros((3,3))
	vHat[0,1], vHat[0,2] = -v[2],v[1]
	vHat[1,0], vHat[1,2] = v[2],-v[0]
	vHat[2,0], vHat[2,1] = -v[1],v[0] 

	return vHat


def angle_axis_to_rotmat(theta, v):
	'''
		Given the axis v, and a rotation theta - convert it into rotation matrix
		theta needs to be in radian
	'''	
	assert theta>=0 and theta<np.pi, "Invalid theta"

	vHat   = axis_to_skewsym(v)
	vHatSq = np.dot(vHat, vHat)
	#Rodrigues Formula
	rotMat = np.eye(3) + math.sin(theta) * vHat + (1 - math.cos(theta)) * vHatSq
	return rotMat
	 

def rotmat_to_angle_axis(rotMat):
	'''
		Converts a rotation matrix into angle axis format
	'''
	aa = linalg.logm(rotMat)
	aa = (aa - aa.transpose()	)/2.0
	v1,v2,v3 = -aa[1,2], aa[0,2], -aa[0,1]
	v  = np.array((v1,v2,v3))
	theta = np.linalg.norm(v)
	v     = v/theta
	return theta, v


def plot_rotmats(rotMats):
	N = rotMats.shape[0]
	#for i in range(N):
		


def generate_random_rotmats(numMat = 100, thetaRange=np.pi/4):
	rotMats = np.zeros((numMat,3,3))
	#Randomly generate an axis for rotation matrix
	v    = np.random.random(3)
	for i in range(numMat):
		theta      = thetaRange * np.random.random()					
		rotMats[i] = angle_axis_to_rotmat(theta, v)
	return rotMats


	
