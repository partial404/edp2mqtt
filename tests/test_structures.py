# pylint: disable=invalid-name, protected-access, missing-function-docstring
"""
Tests for structures module
"""
from edp2mqtt.structures import PackageRegistry


def test_PackageRegistry_bufferRollover():
    reg = PackageRegistry(size=4)
    reg.register(0)
    assert reg._seen_buffer == [True, None, None, None]
    assert reg._last_head == 0
    reg.register(1)
    assert reg._seen_buffer == [True, True, None, None]
    assert reg._last_head == 1
    reg.register(2)
    assert reg._seen_buffer == [True, True, True, None]
    assert reg._last_head == 2
    reg.register(3)
    assert reg._seen_buffer == [True, True, True, True]
    assert reg._last_head == 3
    reg.register(4)
    assert reg._seen_buffer == [True, True, True, True]
    assert reg._last_head == 4


def test_PackageRegistry_outOfOrderNumber():
    reg = PackageRegistry(size=4)
    assert reg.register(0)
    assert reg.register(2)
    assert reg.register(1)
    assert reg._last_head == 2
    assert reg.register(3)
    assert reg._last_head == 3


def test_PackageRegistry_duplicateNumber():
    reg = PackageRegistry(size=4)
    assert reg.register(0)
    assert reg.register(1)
    assert not reg.register(1)
    assert reg.register(2)


def test_PackageRegistry_lostNumber():
    reg = PackageRegistry(size=4)
    assert reg.register(0)
    assert reg.register(2)
    assert reg.register(3)
    assert reg._seen_buffer == [True, False, True, True]


def test_PackageRegistry_reset():
    reg = PackageRegistry(size=4)
    reg.register(0)
    reg.register(1)
    assert reg.register(5)
    assert reg._seen_buffer == [None, True, None, None]
    assert reg._last_head == 5


def test_PackageRegistry_numberRollover():
    reg = PackageRegistry(size=4)
    reg.register(4)
    reg.register(5)
    reg.register(6)
    reg.register(7)
    reg.register(0)
    assert reg._last_head == 0
    assert reg._prev_overflow == 8
