#!/usr/bin/env python3

'''Test for SOA events and planning thereof'''

from dnstest.utils import *
from dnstest.test import Test
import random

EXPIRE_SLEEP = 4

def test_refresh(slave):
    resp = slave.dig("example.", "SOA")
    resp.check(rcode="NOERROR")
    t.sleep(EXPIRE_SLEEP)
    resp = slave.dig("example.", "SOA")
    resp.check(rcode="NOERROR")
    
def test_expire(slave):
    resp = slave.dig("example.", "SOA")
    resp.check(rcode="NOERROR")
    t.sleep(EXPIRE_SLEEP)
    resp = slave.dig("example.", "SOA")
    resp.check(rcode="SERVFAIL")

def test_run(t, action):
    master = t.server("bind")
    master.disable_notify = True

    slave = t.server("knot")
    slave.disable_notify = True
    slave.max_conn_idle = "1s"

    # this zone has refresh = 1s, retry = 1s and expire = 1s + 2s for connection timeouts
    zone = t.zone("example.", storage=".")

    t.link(zone, master, slave)
    t.start()

    slave.zone_wait(zone)
    action(t, slave) # action should keep the event intact
    #test that zone does not expire when master is alive
    detail_log("Refresh - master alive")
    test_refresh(slave)
    master.stop()
    #test that zone does expire when master is down
    action(t, slave) # action should keep the event intact
    detail_log("Refresh - master down")
    test_expire(slave)

    #update master zone file with 10s retry in SOA
    master.update_zonefile(zone, version=1)
    master.start()

    slave.reload() #get new zone file
    slave.zone_wait(zone)
    #stop the master and start it again
    master.stop()
    t.sleep(EXPIRE_SLEEP)
    master.start()

    #zone should expire, retry is pending now
    detail_log("Retry - master dead then alive")
    resp = slave.dig("example.", "SOA")
    resp.check(rcode="SERVFAIL")

    #switch server roles, slave becomes master - there should be no expire
    master.stop()
    slave.zones = {}
    master.zones = {}
    t.link(zone, slave)
    t.generate_conf()
    action(t, slave)

    #test that the zone does not expire
    slave.zone_wait(zone)
    t.sleep(EXPIRE_SLEEP)
    detail_log("Expire - roles switch")
    slave.zone_wait(zone)

    #switch again - zone should expire now
    slave.zones = {}
    t.link(zone, master, slave)
    t.generate_conf()
    action(t, slave)

    detail_log("Expire - roles switch 2")
    test_expire(slave)

    t.stop()

def reload_server(t, s):
    s.reload()
    t.sleep(1)

def restart_server(t, s):
    s.stop()
    s.start()

def reload_or_restart(t, s):
    if random.choice([True, False]):
        restart_server(t, s)
    else:
        reload_server(t, s)

t = Test()

random.seed()

test_run(t, reload_server)
test_run(t, restart_server)
test_run(t, reload_or_restart)


