#!/usr/bin/env python3
"""Check every Thrive Messenger sound theme has every event as a valid, short WAV.

Usage: python3 verify_sounds.py   (needs sox's `soxi` on PATH)
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEMES = ['default', 'galaxia', 'skype', 'flexpbx']
EVENTS = ['message_read', 'call_connected', 'call_ended', 'contact_offline', 'contact_online', 'file_error',
          'file_receive', 'file_send', 'group_call_join', 'group_call_leave', 'incoming_call',
          'login', 'logout', 'outgoing_call', 'receive', 'send',
          'call_busy', 'call_missed', 'voicemail_left', 'voicemail_new', 'voice_message_send',
          'voice_message_receive', 'recording_start', 'recording_stop', 'typing', 'copied',
          'message_deleted', 'message_edited', 'connection_lost', 'reconnected']
LIMIT = {'typing': 0.3, 'copied': 0.3}
MAX = 7.0


def soxi(flag, path):
    return subprocess.check_output(['soxi', flag, path], stderr=subprocess.STDOUT).decode().strip()


fails = []
ok = 0
for th in THEMES:
    for ev in EVENTS:
        p = os.path.join(HERE, th, ev + '.wav')
        tag = '%s/%s.wav' % (th, ev)
        if not os.path.isfile(p):
            fails.append(tag + ': missing')
            continue
        try:
            if soxi('-t', p) != 'wav':
                fails.append(tag + ': not a WAV')
                continue
            d = float(soxi('-D', p))
        except (subprocess.CalledProcessError, ValueError) as e:
            fails.append(tag + ': invalid (%s)' % e)
            continue
        lim = LIMIT.get(ev, MAX)
        if d > lim:
            fails.append(tag + ': %.2f s is longer than %.1f s' % (d, lim))
            continue
        ok += 1
        print('OK   %-40s %5.2f s' % (tag, d))

total = len(THEMES) * len(EVENTS)
print('\n%d themes x %d events = %d checks: %d passed, %d failed' % (len(THEMES), len(EVENTS), total, ok, len(fails)))
for f in fails:
    print('FAIL ' + f)
sys.exit(1 if fails else 0)
