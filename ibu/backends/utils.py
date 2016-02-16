from __future__ import unicode_literals

import datetime
import decimal
import hashlib
import logging
from time import time

import six


logger = logging.getLogger('ibu.backends')


class CursorWrapper(object):
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    WRAP_ERROR_ATTRS = frozenset(
        ['fetchone', 'fetchmany', 'fetchall', 'nextset'])

    def __getattr__(self, attr):
        cursor_attr = getattr(self.cursor, attr)
        if attr in CursorWrapper.WRAP_ERROR_ATTRS:
            return self.db.wrap_database_errors(cursor_attr)
        else:
            return cursor_attr

    def __iter__(self):
        with self.db.wrap_database_errors:
            for item in self.cursor:
                yield item

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # Ticket #17671 - Close instead of passing thru to avoid backend
        # specific behavior. Catch errors liberally because errors in cleanup
        # code aren't useful.
        try:
            self.close()
        except self.db.Database.Error:
            pass

    # The following methods cannot be implemented in __getattr__, because the
    # code must run when the method is invoked, not just when it is accessed.

    def callproc(self, procname, params=None):
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            if params is None:
                return self.cursor.callproc(procname)
            else:
                return self.cursor.callproc(procname, params)

    def execute(self, sql, params=None):
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            if params is None:
                return self.cursor.execute(sql)
            else:
                return self.cursor.execute(sql, params)

    def executemany(self, sql, param_list):
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            return self.cursor.executemany(sql, param_list)


class CursorDebugWrapper(CursorWrapper):

    # XXX callproc isn't instrumented at this time.

    def execute(self, sql, params=None):
        start = time()
        try:
            return super(CursorDebugWrapper, self).execute(sql, params)
        finally:
            stop = time()
            duration = stop - start
            sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            self.db.queries_log.append({
                'sql': sql,
                'time': "%.3f" % duration,
            })
            logger.debug('(%.3f) %s; args=%s', duration, sql, params,
                         extra={
                             'duration': duration,
                             'sql': sql, 'params': params}
                         )

    def executemany(self, sql, param_list):
        start = time()
        try:
            return super(CursorDebugWrapper, self).executemany(sql, param_list)
        finally:
            stop = time()
            duration = stop - start
            try:
                times = len(param_list)
            except TypeError:           # param_list could be an iterator
                times = '?'
            self.db.queries_log.append({
                'sql': '%s times: %s' % (times, sql),
                'time': "%.3f" % duration,
            })
            logger.debug('(%.3f) %s; args=%s', duration, sql, param_list,
                         extra={
                             'duration': duration, 'sql': sql,
                             'params': param_list}
                         )


###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    # returns None if s is null
    return datetime.date(*map(int, s.split('-'))) if s else None


def typecast_time(s):  # does NOT store time zone information
    if not s:
        return None
    hour, minutes, seconds = s.split(':')
    if '.' in seconds:  # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.time(int(hour), int(minutes), int(seconds),
                         int(float('.' + microseconds) * 1000000))


def typecast_timestamp(s):  # does NOT store time zone information
    # "2005-07-29 15:48:00.590358-05"
    # "2005-07-29 09:56:00-05"
    if not s:
        return None
    if ' ' not in s:
        return typecast_date(s)
    d, t = s.split()
    # Extract timezone information, if it exists. Currently we just throw
    # it away, but in the future we may make use of it.
    if '-' in t:
        t, tz = t.split('-', 1)
        tz = '-' + tz
    elif '+' in t:
        t, tz = t.split('+', 1)
        tz = '+' + tz
    else:
        tz = ''
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds:  # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'

    return datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]),
                             int(times[0]), int(times[1]), int(seconds),
                             int((microseconds + '000000')[:6]), 'UTC')


def typecast_decimal(s):
    if s is None or s == '':
        return None
    return decimal.Decimal(s)


###############################################
# Converters from Python to database (string) #
###############################################

def rev_typecast_decimal(d):
    if d is None:
        return None
    return str(d)


def truncate_name(name, length=None, hash_len=4):
    """Shortens a string to a repeatable mangled version with the given length.
    """
    if length is None or len(name) <= length:
        return name

    hsh = hashlib.md5(force_bytes(name)).hexdigest()[:hash_len]
    return '%s%s' % (name[:length - hash_len], hsh)


def format_number(value, max_digits, decimal_places):
    """
    Formats a number into a string with the requisite number of digits and
    decimal places.
    """
    if value is None:
        return None
    if isinstance(value, decimal.Decimal):
        context = decimal.getcontext().copy()
        if max_digits is not None:
            context.prec = max_digits
        if decimal_places is not None:
            value = value.quantize(
                decimal.Decimal(".1") ** decimal_places, context=context)
        else:
            context.traps[decimal.Rounded] = 1
            value = context.create_decimal(value)
        return "{:f}".format(value)
    if decimal_places is not None:
        return "%.*f" % (decimal_places, value)
    return "{:f}".format(value)


class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """

    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args + moreargs), **dict(kwargs, **morekwargs))
    return _curried


class EscapeData(object):
    pass


class EscapeBytes(bytes, EscapeData):
    """
    A byte string that should be HTML-escaped when output.
    """
    pass


class EscapeText(six.text_type, EscapeData):
    """
    A unicode string object that should be HTML-escaped when output.
    """
    pass

if six.PY3:
    EscapeString = EscapeText
else:
    EscapeString = EscapeBytes
    # backwards compatibility for Python 2
    EscapeUnicode = EscapeText


class SafeData(object):
    def __html__(self):
        """
        Returns the html representation of a string for interoperability.

        This allows other template engines to understand Django's SafeData.
        """
        return self


class SafeBytes(bytes, SafeData):
    """
    A bytes subclass that has been specifically marked as "safe" (requires no
    further escaping) for HTML output purposes.
    """

    def __add__(self, rhs):
        """
        Concatenating a safe byte string with another safe byte string or safe
        unicode string is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeBytes, self).__add__(rhs)
        if isinstance(rhs, SafeText):
            return SafeText(t)
        elif isinstance(rhs, SafeBytes):
            return SafeBytes(t)
        return t

    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, bytes):
            return SafeBytes(data)
        else:
            return SafeText(data)

    decode = curry(_proxy_method, method=bytes.decode)


class SafeText(six.text_type, SafeData):
    """
    A unicode (Python 2) / str (Python 3) subclass that has been specifically
    marked as "safe" for HTML output purposes.
    """

    def __add__(self, rhs):
        """
        Concatenating a safe unicode string with another safe byte string or
        safe unicode string is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeText, self).__add__(rhs)
        if isinstance(rhs, SafeData):
            return SafeText(t)
        return t

    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, bytes):
            return SafeBytes(data)
        else:
            return SafeText(data)

    encode = curry(_proxy_method, method=six.text_type.encode)

if six.PY3:
    SafeString = SafeText
else:
    SafeString = SafeBytes
    # backwards compatibility for Python 2
    SafeUnicode = SafeText
