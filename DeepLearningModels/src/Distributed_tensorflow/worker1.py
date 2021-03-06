# -*- coding: utf-8 -*-
#! /usr/bin/env python
"""
Created on Thu Apr 19 08:52:30 2018

@author: zy
"""

import tensorflow as tf
import numpy as np
import os
import matplotlib.pyplot as plt

'''
分布式计算
'''

'''
(1)为每个角色添加IP地址和端口，创建worker 
'''

'''定义IP和端口号'''
#指定服务器ip和port
strps_hosts = '192.168.43.205:1234'
#指定两个终端的ip和port
strworker_hosts =  '192.168.43.206:1235,192.168.43.207:1236'

#定义角色名称
strjob_name = 'worker'
task_index = 0
#将字符串转为数组
ps_hosts = strps_hosts.split(',')
worker_hosts = strworker_hosts.split(',')
cluster_spec = tf.train.ClusterSpec({'ps': ps_hosts,'worker': worker_hosts})

#创建server
server = tf.train.Server(
         cluster_spec,
         job_name = strjob_name,
         task_index = task_index)

'''
(2) 为ps角色添加等待函数
'''
#ps角色处于监听状态，等待终端连接
if strjob_name == 'ps':
    print('waiting....')
    server.join()
    
    
    
'''
(3) 创建网络结构
'''


#设定训练集数据长度
n_train = 100

#生成x数据，[-1,1]之间，均分成n_train个数据
train_x = np.linspace(-1,1,n_train).reshape(n_train,1)

#把x乘以2，在加入(0,0.3)的高斯正太分布
train_y = 2*train_x + np.random.normal(loc=0.0,scale=0.3,size=[n_train,1])

#绘制x,y波形
plt.figure()
plt.plot(train_x,train_y,'ro',label='y=2x')   #o使用圆点标记一个点
plt.legend()
plt.show()

#创建网络结构时，通过tf.device()函数将全部的节点都放在当前任务下
with tf.device(tf.train.replica_device_setter(
        worker_device = '/job:worker/task:{0}'.format(task_index),
        cluster = cluster_spec)):
    
    '''
    前向反馈
    '''
    #创建占位符
    input_x = tf.placeholder(dtype=tf.float32)
    input_y = tf.placeholder(dtype=tf.float32)
    
    #模型参数
    w = tf.Variable(tf.truncated_normal(shape=[1],mean=0.0,stddev=1),name='w')    #设置正太分布参数  初始化权重
    b = tf.Variable(tf.truncated_normal(shape=[1],mean=0.0,stddev=1),name='b')    #设置正太分布参数  初始化偏置
    
    #创建一个global_step变量
    global_step = tf.train.get_or_create_global_step()
    
    #前向结构
    pred = tf.multiply(w,input_x) + b
    
    #将预测值以直方图形式显示，给直方图命名为'pred'
    tf.summary.histogram('pred',pred)
    
    '''
    反向传播bp
    '''
    #定义代价函数  选取二次代价函数
    cost = tf.reduce_mean(tf.square(input_y - pred))
    
    #将损失以标量形式显示 该变量命名为loss_function
    tf.summary.scalar('loss_function',cost)
    
    
    #设置求解器 采用梯度下降法 学习了设置为0.001 并把global_step变量放到优化器中，这样每运行一次优化器，global_step就会自动获得当前迭代的次数
    train = tf.train.GradientDescentOptimizer(learning_rate=0.001).minimize(cost,global_step = global_step)
    
    saver = tf.train.Saver(max_to_keep = 1)
    
    #合并所有的summary
    merged_summary_op = tf.summary.merge_all()
    
    #初始化所有变量，因此变量需要放在其前面定义
    init  =tf.global_variables_initializer()

'''
(4)创建Supervisor，管理session
'''    
training_epochs = 2000
display_step = 20

sv = tf.train.Supervisor(is_chief = (task_index == 0),          #0号worker为chief
                         logdir='./LinearRegression/super/',    #检查点和summary文件保存的路径
                         init_op = init,  #初始化所有变量
                         summary_op = None,                            #summary_op用于自动保存summary文件，设置为None，表示不自动保存
                         saver = saver,   #将保存检查点的saver对象传入，supervisor会自动保存检查点文件。否则设置为None
                         global_step = global_step,
                         save_model_secs = 50   #保存检查点文件的时间间隔
                         )





'''
(5) 迭代训练
'''
#连接目标角色创建session
with sv.managed_session(server.target) as sess:
    print("sess ok：")
    print(global_step.eval(session=sess))
    print('开始迭代：')
         
    #存放批次值和代价值
    plotdata = {'batch_size':[],'loss':[]}
    
    #开始迭代 这里step表示当前执行步数，迭代training_epochs轮  需要执行training_epochs*n_train步
    for step in range(training_epochs*n_train):
        for (x,y) in zip(train_x,train_y):
            #开始执行图  并返回当前步数
            _,step = sess.run([train,global_step],feed_dict={input_x:x,input_y:y})
                                            
            #生成summary
            summary_str = sess.run(merged_summary_op,feed_dict={input_x:x,input_y:y})
            #将summary写入文件  手动保存summary日志文件
            sv.summary_computed(sess,summary_str,global_step = step)
            
            
             #一轮训练完成后 打印输出信息
            if step % display_step == 0:
                #计算代价值
                loss = sess.run(cost,feed_dict={input_x:train_x,input_y:train_y})
                print('step {0}  cost {1}  w {2}  b{3}'.format(step,loss,sess.run(w),sess.run(b)))
        
                #保存每display_step轮训练后的代价值以及当前迭代轮数
                if not loss == np.nan:
                    plotdata['batch_size'].append(step)
                    plotdata['loss'].append(loss)
                
        
    print('Finished!')
    #手动保存检查点文件
    #sv.saver.save(sess,'./LinearRegression/sv/sv.cpkt',global_step = step)
    
sv.stop()