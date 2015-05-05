#!/bin/env python
# -*- coding: utf-8 -*-
"""
XBee Wifi Network Message Process in Python
----------------------------------------

Author: Zheng GONG(matthewzhenggong@gmail.com)

This file is part of FIWT.

FIWT is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 3.0 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library.
"""
import socket, time, traceback
import XBeeIPServices
import PayloadPackage
from MessageFuncs import process_funcs

at_status = {
    0: 'OK',
    1: 'ERROR',
    2: 'Invalid Command',
    3: 'Invalid Parameter',
    4: 'Tx Failure',
}


class XBeeNetwork(object):
    def __init__(self, parent, hosts):
        self.parent = parent
        self.log = parent.log
        self.arrv_cnt = 0
        self.arrv_bcnt = 0
        host = hosts[0][0]
        self.socklist = []
        for i in hosts :
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind((host,i[1]))
                sock.setblocking(0)
                self.socklist.append(sock)
            except:
                self.log.error(traceback.format_exc())
        self.socklist_set = set(self.socklist)
        self.tx_socket = self.socklist[0]

        self.service = XBeeIPServices.XBeeApplicationService(host)
        self.socklist.append(self.service.sock)

    def getReadList(self):
        return self.socklist

    def read(self, rlist, recv_ts):
        rlist = self.socklist_set.intersection(rlist)
        for rx in rlist:
            (rf_data,address)=rx.recvfrom(1400)
            data = {'id':'rx', 'source_addr':address, 'rf_data':rf_data}
            self.process(data, recv_ts)

        if self.service.sock in rlist:
            data = self.service.getPacket()
            if data:
                self.process(data, recv_ts)

    def updateStatistics(self, bcnt):
            elapsed = time.clock() - self.parent.T0
            if elapsed <= 0:
                self.arrv_cnt = 0
                self.arrv_bcnt = 0
            else:
                self.arrv_cnt += 1
                self.arrv_bcnt += bcnt
                if (self.arrv_cnt % 500) == 0 :
                    self.parent.msgc2guiQueue.put_nowait({'ID':'Statistics',
                            'arrv_cnt':self.arrv_cnt, 'arrv_bcnt':self.arrv_bcnt,
                            'elapsed':self.elapsed})

    def process(self, data, recv_ts) :
        if data['id'] == 'rx':
            try:
              addr = data['source_addr']
              data_group = data['rf_data']
              self.updateStatistics(len(data_group))
              rf_data_group,sent_ts = PayloadPackage.unpack(data_group)
              for gen_ts,rf_data in rf_data_group :
                process_funcs[rf_data[0]](self, rf_data, gen_ts, sent_ts, recv_ts, addr)
            except:
                self.log.error(repr(data))
                self.log.error(traceback.format_exc())
        elif data['id'] == 'remote_at_response':
            try:
                s = data['status']
                addr = data['source_addr']
                parameter = data['parameter']
                if self.frame_id != data['frame_id']:
                    self.log.error("Remote ATResponse frame_id mismatch")
                self.log.info('ATResponse:{} {}={} from {}'.format(
                    at_status[s], data['command'],
                    ':'.join('{:02x}'.format(ord(c)) for c in parameter),
                     addr))
            except:
                self.log.error(traceback.format_exc())
                self.log.error(repr(data))
        else:
            self.log.info(repr(data))


