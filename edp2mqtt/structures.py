"""
Module with custom structures
"""

import logging

logger = logging.getLogger(__name__)


class PackageRegistry:
    """
    Structure that keeps track if a potentially out of order, but sequenced
    number has been seen before. This is achieved by having a running buffer of
    size N, relative to the highest number seen. I.e. the buffer is able to
    check tell whether a number has been seen before if it is N greater or lower
    than previously the highest number.seen. Overflow/wraparound is also
    supported. It is assumed that the wraparound number is even multiple of
    the buffer size (N).

    If a number, falls outside the buffer bounds (N lower or greater than
    previously the highest number), including potential wrap around, then the
    buffer is reset and the new number is assumed to be the highest.

    This class is useful for keeping track if a EDP package has previously been
    seen or not.
    """

    def __init__(self, size=256):
        """
        Constructor...

        :param size: Size of buffer, must be a power of two.
        """
        assert size > 2 and (size & (size - 1)) == 0
        self._size = size
        self._seen_buffer = [None for i in range(0, size)]
        self._last_head = None
        self._prev_overflow = None

    def __str__(self):  # pylint: disable=missing-function-docstring
        return (
            f"buffer: {self._seen_buffer}, last head: {self._last_head}, "
            f"previous overflow: {self._prev_overflow}"
        )

    def register(self, number):
        """
        Register a new number.

        :param number: Number to register
        :return: True for unseen numbers, otherwise False
        """
        assert number >= 0
        logger.debug("%d...", number)
        new_index = number % self._size
        if self._last_head is None:
            logger.debug("  ... new")
            self._last_head = number
            self._seen_buffer[new_index] = True
            return True
        last_index = self._last_head % self._size
        if self._last_head - self._size < number <= self._last_head:
            # Older number
            logger.debug("  ... order")
            if self._seen_buffer[new_index]:
                logger.debug("  ... seen before")
                return False
            self._seen_buffer[new_index] = True
        elif (
            self._last_head < number < self._last_head + self._size
            or number < last_index
        ):
            logger.debug("  ... higher")
            if number < last_index:
                self._prev_overflow = self._last_head + (self._size - last_index)
                logger.debug("  ... wraparound")
            # New higher
            if new_index < last_index:
                # Handle wrap around in buffer
                logger.debug("  ... buffer wraparound")
                for i in range(last_index + 1, self._size):
                    if self._seen_buffer[i] is False:
                        logger.debug(
                            "  ... %d never received!",
                            i - last_index + self._last_head - self._size,
                        )
                    self._seen_buffer[i] = False
                last_index = -1
            for i in range(last_index + 1, new_index + 1):
                if self._seen_buffer[i] is False:
                    # Not correct:
                    lost_number = i - last_index + self._last_head - self._size
                    if lost_number < 0:
                        lost_number += self._prev_overflow
                        logger.debug("  ... %d never received!", lost_number)
                self._seen_buffer[i] = False
            self._seen_buffer[new_index] = True
            self._last_head = number
        else:
            # Reset
            logger.debug(
                "  ... %d is far away from any number previously seen, last seen %d",
                number,
                self._last_head,
            )
            self._prev_overflow = None
            self._last_head = number
            self._seen_buffer = [None for i in range(0, self._size)]
            self._seen_buffer[new_index] = True
        return True
