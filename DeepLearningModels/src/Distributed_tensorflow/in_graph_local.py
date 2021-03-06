# -*- coding: utf-8 -*-
import tensorflow as tf
from multiprocessing import Process
from time import sleep
import os

'''
in_graph 单机版本
'''

cluster = tf.train.ClusterSpec({"worker": ["localhost:3333","localhost:3334",], "ps": ["localhost:3335"]})

def parameter_server():
    server = tf.train.Server(cluster, job_name="ps", task_index=0)
    sess = tf.Session(target=server.target)
    
    print("Parameter server: blocking...")
    server.join()


def worker(worker_n):
    server = tf.train.Server(cluster, job_name="worker", task_index=worker_n)
    
    if 0 == worker_n:
        with tf.device("/job:ps/task:0"):
            var = tf.Variable(2.0, name='var')
            var1 = tf.Variable(1.0, name='var1')
        with tf.device("/job:worker/task:0"):
            pred = var + var1;
        with tf.device("/job:worker/task:1"):
            loss = 2*pred
        
        sess = tf.Session(target=server.target, config=tf.ConfigProto(log_device_placement=True))
        print("Parameter server: waiting for cluster connection...")
        sess.run(tf.report_uninitialized_variables())
        print("Parameter server: cluster ready!")
        
        print("Parameter server: initializing variables...")
        sess.run(tf.global_variables_initializer())
        print("Parameter server: variables initialized")
        
        print("gjl start")
        print(sess.run(loss))	
        #sess.run(loss)
    
    print("Worker %d: blocking..." % worker_n)
    server.join()


if __name__ == "__main__":
	ps_proc = Process(target=parameter_server, daemon=True)
	w1_proc = Process(target=worker, args=(0, ), daemon=True)
	w2_proc = Process(target=worker, args=(1, ), daemon=True)
	ps_proc.start()
	w1_proc.start()
	w2_proc.start()
	ps_proc.join()
	w1_proc.join()
	w2_proc.join()
	print("end")


#for proc in [w1_proc, w2_proc, ps_proc]:
#    proc.terminate()
