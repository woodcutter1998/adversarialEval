# coding: utf-8
# Author: Jerry Kong     jerry.kong@wustl.edu
# Usage: Import and run
# Note: Model structure copied from tensorflow official website


#import library
import tensorflow as tf     #cpu tensorflow   (may work on gpu)
from tensorflow import keras        #use keras as frontend
import os
# Helper libraries
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as op


class cfind():
    """
    A generic cfinder class for adversarial sampel generation
    No batch support, slow
    """
    def __init__(self, seed, seed_label, model=None, checkpoint_path = None, constraint = None):
        """
        cfind object constructor
        
        :param seed: set of benign samples to be transformed to malisious samples
        :param seed_label: labels fo seed
        :param model: the model structure to be used in optimization
        :param checkpoint_path: where the model weight is saved in the format of check_point
        :param constrain: an array of constraints where each row correspons to one pixel in the seed
        """
        self.adv_seed = seed
        self.adv_seed_label = seed_label
        self.model = model
        self.input_shape = seed[0].shape
        tp = list(self.input_shape)
        tp.insert(0,1)
        self.input_shape_p = tuple(tp)
        self.flat_length = 1
        self.fail_list = []
        for i in self.input_shape:
            self.flat_length*=i
        self.checkpoint_path = checkpoint_path
        if constraint == None:
            self.constraint = [[0,1]]*(self.flat_length)
        else:
            self.constraint = constraint
    
    def gradfunc(self, x, c, img, loss, grad):
        """
        Generate gradient and loss value
        Handled by scipy optimization
        :param x: current guess
        :param c: current c
        :param img: the original sample
        :param loss: loss tensor
        :param grad: loss gradient tensor
        """
        ad = x.reshape(self.input_shape_p)
        grad_val = self.sess.run(grad,feed_dict={self.intensor: ad})
        loss_val = loss.eval(feed_dict={self.intensor: ad},session = self.sess)
        y = np.linalg.norm(ad-img)*c + loss_val
        gra = (np.array(grad_val, dtype = np.float64)+c*(2*ad[0]-2*img)).flatten()
        return y[0], gra
    
    def test_initialize(self):
        """
        initialize series of tensor and tensorflow session
        """
        self.sess = tf.Session()
        keras.backend.set_session(self.sess)
        self.model.load_weights(self.checkpoint_path)
        self.testensor = tf.convert_to_tensor([0])
        self.intensor = self.model.input
        self.outtensor = self.model.output
        self.lo = keras.losses.sparse_categorical_crossentropy(self.testensor,self.outtensor)
        self.g = tf.gradients(self.lo, self.intensor)

    
    
    def cfinder(self,img, label, epi = 0.001, c = 20):
        """
        find largest c possible for a specific sample img
        :param img: target sample
        :param label: sample label
        :param epi: threshold for determining the exit condition. optimal c is with in [return c, return c + epi]
        :param c: initial guess for c
        """
        flag=0
        for t in range(10):
            if t == label:
                continue
            self.testensor = tf.convert_to_tensor([t])
            self.lo = keras.losses.sparse_categorical_crossentropy(self.testensor,self.outtensor)
            self.g = tf.gradients(self.lo, self.intensor)
            eval_lo = self.lo
            eval_g = self.g
            clast = c
            noise = np.random.uniform(size=self.input_shape).flatten()/10
            l = label
            while l != t:
                clast = c
                c = c/2
                ad = op.minimize(self.gradfunc, noise, method = 'L-BFGS-B', jac = True,args=(c, img, eval_lo, eval_g), bounds = self.constraint)
                asample = ad.x.reshape(self.input_shape_p)
                l = np.argmax(self.model.predict(asample))
                if clast-c<epi:
                    break
            if l==t:
                flag=1
                break
        if flag==0:
            raise Exception('bad initial guess, unable to find c')
        while clast-c >epi:
            cmid = (clast+c)/2
            ad = op.minimize(self.gradfunc, noise, method = 'L-BFGS-B', jac = True,args=(cmid, img, eval_lo, eval_g), bounds = self.constraint)
            asample = ad.x.reshape(self.input_shape_p)
            l = np.argmax(self.model.predict(asample))
            if l != t:
                clast = cmid
            else:
                c = cmid
        ad = op.minimize(self.gradfunc, noise, method = 'L-BFGS-B', jac = True,args=(c, img, eval_lo, eval_g), bounds = self.constraint)
        asample = ad.x.reshape(self.input_shape_p)
        return c, asample[0]
        
    def findAd(self):
        """
        adversarial sample finding driver
        """
        self.maxc = np.zeros(self.adv_seed_label.shape)
        self.adv_sample = np.zeros(self.adv_seed.shape)
        for i,v in enumerate(self.adv_seed):
            try:
                self.maxc[i], self.adv_sample[i] = self.cfinder(v,self.adv_seed_label[i])
            except Exception as error:
                print(error)
                self.maxc[i] = 0
                self.adv_sample[i] = v
                self.fail_list.append(i)
        
    def setModel(self,model):
        self.model = model
    
    def setPath(self, cpp):
        self.checkpoint_path = cpp
    
    def setConstraint(self, cs):
        self.constraint = cs
        
    def getModel(self):
        return self.model
    
    def getC(self):
        return self.maxc
    
    def getAdvSample(self):
        return self.adv_sample            