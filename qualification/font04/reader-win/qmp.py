#!/usr/bin/env python3
"""Tiny QMP client: qmp.py screendump out.png | qmp.py keys 'ret' 'spc' ... | qmp.py type 'text' | qmp.py raw '{json}'"""
import json, socket, sys, os
sock = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qmp.sock')
s = socket.socket(socket.AF_UNIX); s.connect(sock); f = s.makefile('rw')
def rx():
    while True:
        m = json.loads(f.readline())
        if 'event' not in m: return m
def cmd(name, **args):
    f.write(json.dumps({'execute': name, 'arguments': args} if args else {'execute': name}) + '\n'); f.flush(); return rx()
rx(); cmd('qmp_capabilities')
op = sys.argv[1]
if op == 'screendump': print(cmd('screendump', filename=os.path.abspath(sys.argv[2]), format='png'))
elif op == 'keys':
    for k in sys.argv[2:]: print(cmd('send-key', keys=[{'type': 'qcode', 'data': x} for x in k.split('+')]))
elif op == 'raw': print(cmd(**json.loads(sys.argv[2])) if False else cmd(json.loads(sys.argv[2])['execute'], **json.loads(sys.argv[2]).get('arguments', {})))
elif op == 'status': print(cmd('query-status'))
if op == 'click':
    x, y, W, H = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1280, int(sys.argv[5]) if len(sys.argv) > 5 else 800
    ev = lambda *e: cmd('input-send-event', events=list(e))
    print(ev({'type': 'abs', 'data': {'axis': 'x', 'value': x * 32767 // (W - 1)}}, {'type': 'abs', 'data': {'axis': 'y', 'value': y * 32767 // (H - 1)}}))
    import time; time.sleep(0.2)
    print(ev({'type': 'btn', 'data': {'down': True, 'button': 'left'}})); time.sleep(0.1)
    print(ev({'type': 'btn', 'data': {'down': False, 'button': 'left'}}))
