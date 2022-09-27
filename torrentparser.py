#!/usr/bin/env python
# coding: utf-8

"""
Code yanked from https://github.com/7sDream/torrent_parser/blob/master/torrent_parser.py

Slightly modified because easier
"""

from __future__ import print_function, unicode_literals

import argparse
import binascii
import collections
import io
import json
import sys
import warnings

try:
    FileNotFoundError
except NameError:
    # Python 2 do not have FileNotFoundError, use IOError instead
    # noinspection PyShadowingBuiltins
    FileNotFoundError = IOError

try:
    # noinspection PyPackageRequirements
    from chardet import detect as _detect
except ImportError:

    def _detect(_):
        warnings.warn("No chardet module installed, encoding will be utf-8")
        return {"encoding": "utf-8", "confidence": 1}

try:
    # noinspection PyUnresolvedReferences
    # For Python 2
    str_type = unicode
    bytes_type = str
except NameError:
    # For Python 3
    str_type = str
    bytes_type = bytes

__all__ = [
    "InvalidTorrentDataException",
    "BEncoder",
    "BDecoder",
    "encode",
    "decode",
    "TorrentFileParser",
    "TorrentFileCreator",
    "create_torrent_file",
    "parse_torrent_file",
]

__version__ = "0.4.1"


def detect(content):
    return _detect(content)["encoding"]


class InvalidTorrentDataException(Exception):
    def __init__(self, pos, msg=None):
        msg = msg or "Invalid torrent format when read at pos {pos}"
        msg = msg.format(pos=pos)
        super(InvalidTorrentDataException, self).__init__(msg)


class __EndCls(object):
    pass


_END = __EndCls()


def _check_hash_field_params(name, value):
    return (
        isinstance(name, str_type)
        and isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], bool)
    )


class BDecoder(object):

    TYPE_LIST = "list"
    TYPE_DICT = "dict"
    TYPE_INT = "int"
    TYPE_STRING = "string"
    TYPE_END = "end"

    LIST_INDICATOR = b"l"
    DICT_INDICATOR = b"d"
    INT_INDICATOR = b"i"
    END_INDICATOR = b"e"
    STRING_INDICATOR = b""
    STRING_DELIMITER = b":"

    TYPES = [
        (TYPE_LIST, LIST_INDICATOR),
        (TYPE_DICT, DICT_INDICATOR),
        (TYPE_INT, INT_INDICATOR),
        (TYPE_END, END_INDICATOR),
        (TYPE_STRING, STRING_INDICATOR),
    ]

    # see https://docs.python.org/3/library/codecs.html#error-handlers
    # for other usable error handler string
    ERROR_HANDLER_USEBYTES = "usebytes"

    def __init__(
        self,
        data,
        use_ordered_dict=False,
        encoding="utf-8",
        errors="strict",
        hash_fields=None,
        hash_raw=False,
    ):
        """
        :param bytes|file data: bytes or a **binary** file-like object to parse,
          which means need 'b' mode when use built-in open function
        :param bool use_ordered_dict: Use collections.OrderedDict as dict
          container default False, which mean use built-in dict
        :param str encoding: file content encoding, default utf-8, use 'auto'
          to enable charset auto detection (need 'chardet' package installed)
        :param str errors: how to deal with encoding error when try to parse
          string from content with ``encoding``.
          see https://docs.python.org/3/library/codecs.html#error-handlers
          for usable error handler string.
          in particular, you can use "usebytes" to use "strict" decode mode
          and let it return raw bytes if error happened.
        :param Dict[str, Tuple[int, bool]] hash_fields: extra fields should
          be treated as hash value. dict key is the field name, value is a
          two-element tuple of (hash_block_length, as_a_list).
          See :any:`hash_field` for detail
        """
        if isinstance(data, bytes_type):
            data = io.BytesIO(data)
        elif getattr(data, "read") is not None and getattr(data, "seek") is not None:
            pass
        else:
            raise ValueError("Parameter data must be bytes or file like object")

        self._pos = 0
        self._encoding = encoding
        self._content = data
        self._use_ordered_dict = use_ordered_dict
        self._error_handler = errors
        self._error_use_bytes = False
        if self._error_handler == BDecoder.ERROR_HANDLER_USEBYTES:
            self._error_handler = "strict"
            self._error_use_bytes = True

        self._hash_fields = {}
        if hash_fields is not None:
            for k, v in hash_fields.items():
                if _check_hash_field_params(k, v):
                    self._hash_fields[k] = v
                else:
                    raise ValueError(
                        "Invalid hash field parameter, it should be type of "
                        "Dict[str, Tuple[int, bool]]"
                    )
        self._hash_raw = bool(hash_raw)

    def hash_field(self, name, block_length=20, need_list=False):
        """
        Let field with the `name` to be treated as hash value, don't decode it
        as a string.

        :param str name: field name
        :param int block_length: hash block length for split
        :param bool need_list:  if True, when the field only has one block(
          or even empty) its parse result will be a one-element list(
          or empty list); If False, will be a string in 0 or 1 block condition
        :return: return self, so you can chained call
        """
        v = (block_length, need_list)
        if _check_hash_field_params(name, v):
            self._hash_fields[name] = v
        else:
            raise ValueError("Invalid hash field parameter")
        return self

    def decode(self):
        """
        :rtype: dict|list|int|str|unicode|bytes
        :raise: :any:`InvalidTorrentDataException` when parse failed or error
          happened when decode string using specified encoding
        """
        self._restart()
        data = self._next_element()

        try:
            c = self._read_byte(1, True)
            raise InvalidTorrentDataException(
                0, "Expect EOF, but get [{}] at pos {}".format(c, self._pos)
            )
        except EOFError:  # expect EOF
            pass

        return data

    def _read_byte(self, count=1, raise_eof=False):
        assert count >= 0
        gotten = self._content.read(count)
        if count != 0 and len(gotten) == 0:
            if raise_eof:
                raise EOFError()
            raise InvalidTorrentDataException(
                self._pos, "Unexpected EOF when reading torrent file"
            )
        self._pos += count
        return gotten

    def _seek_back(self, count):
        self._content.seek(-count, 1)
        self._pos = self._pos - count

    def _restart(self):
        self._content.seek(0, 0)
        self._pos = 0

    def _dict_items_generator(self):
        while True:
            k = self._next_element()
            if k is _END:
                return
            if not isinstance(k, str_type) and not isinstance(k, bytes_type):
                raise InvalidTorrentDataException(
                    self._pos, "Type of dict key can't be " + type(k).__name__
                )
            if k in self._hash_fields:
                v = self._next_hash(*self._hash_fields[k])
            else:
                v = self._next_element(k)
            if k == "encoding":
                self._encoding = v
            yield k, v

    def _next_dict(self):
        data = collections.OrderedDict() if self._use_ordered_dict else dict()
        for key, element in self._dict_items_generator():
            data[key] = element
        return data

    def _list_items_generator(self):
        while True:
            element = self._next_element()
            if element is _END:
                return
            yield element

    def _next_list(self):
        return [element for element in self._list_items_generator()]

    def _next_int(self, end=END_INDICATOR):
        value = 0
        char = self._read_byte(1)
        neg = False
        while char != end:
            if not neg and char == b"-":
                neg = True
            elif not b"0" <= char <= b"9":
                raise InvalidTorrentDataException(self._pos - 1)
            else:
                value = value * 10 + int(char) - int(b"0")
            char = self._read_byte(1)
        return -value if neg else value

    def _next_string(self, need_decode=True, field=None):
        length = self._next_int(self.STRING_DELIMITER)
        raw = self._read_byte(length)
        if need_decode:
            encoding = self._encoding
            if encoding == "auto":
                self.encoding = encoding = detect(raw)
            try:
                string = raw.decode(encoding, self._error_handler)
            except UnicodeDecodeError as e:
                if self._error_use_bytes:
                    return raw
                else:
                    msg = [
                        "Fail to decode string at pos {pos} using encoding ",
                        e.encoding,
                    ]
                    if field:
                        msg.extend(
                            [
                                ' when parser field "',
                                field,
                                '"' ", maybe it is an hash field. ",
                                'You can use self.hash_field("',
                                field,
                                '") ',
                                "to let it be treated as hash value, ",
                                "so this error may disappear",
                            ]
                        )
                    raise InvalidTorrentDataException(
                        self._pos - length + e.start, "".join(msg)
                    )
            return string
        return raw

    def _next_hash(self, p_len, need_list):
        raw = self._next_string(need_decode=False)
        if len(raw) % p_len != 0:
            raise InvalidTorrentDataException(
                self._pos - len(raw), "Hash bit length not match at pos {pos}"
            )
        if self._hash_raw:
            return raw
        res = [
            binascii.hexlify(chunk).decode("ascii")
            for chunk in (raw[x : x + p_len] for x in range(0, len(raw), p_len))
        ]
        if len(res) == 0 and not need_list:
            return ""
        if len(res) == 1 and not need_list:
            return res[0]
        return res

    @staticmethod
    def _next_end():
        return _END

    def _next_type(self):
        for (element_type, indicator) in self.TYPES:
            indicator_length = len(indicator)
            char = self._read_byte(indicator_length)
            if indicator == char:
                return element_type
            self._seek_back(indicator_length)
        raise InvalidTorrentDataException(self._pos)

    def _type_to_func(self, t):
        return getattr(self, "_next_" + t)

    def _next_element(self, field=None):
        element_type = self._next_type()
        if element_type is BDecoder.TYPE_STRING and field is not None:
            element = self._type_to_func(element_type)(field=field)
        else:
            element = self._type_to_func(element_type)()
        return element

class TorrentFileParser(object):
    HASH_FIELD_DEFAULT_PARAMS = {
        # field length need_list
        "pieces": (20, True),
        "ed2k": (16, False),
        "filehash": (20, False),
        "pieces root": (32, False),
    }

    def __init__(
        self,
        fp,
        use_ordered_dict=False,
        encoding="utf-8",
        errors=BDecoder.ERROR_HANDLER_USEBYTES,
        hash_fields=None,
        hash_raw=False,
    ):
        """
        See :any:`BDecoder.__init__` for parameter description.
        This class will use some default ``hash_fields`` values, and use "usebytes" as error handler
        compare to use :any:`BDecoder` directly.

        :param file fp: file to be parse
        :param bool use_ordered_dict:
        :param str encoding:
        :param str errors:
        :param Dict[str, Tuple[int, bool]] hash_fields:
        :param bool hash_raw:
        """
        self.dictionary = {}
        torrent_hash_fields = dict(TorrentFileParser.HASH_FIELD_DEFAULT_PARAMS)
        if hash_fields is not None:
            torrent_hash_fields.update(hash_fields)

        self._decoder = BDecoder(
            fp,
            use_ordered_dict,
            encoding,
            errors,
            torrent_hash_fields,
            hash_raw,
        )

    def hash_field(self, name, block_length=20, need_dict=False):
        """
        See :any:`BDecoder.hash_field` for parameter description

        :param name:
        :param block_length:
        :param need_dict:
        :return: return self, so you can chained call
        """
        self._decoder.hash_field(name, block_length, need_dict)
        return self

    def parse(self):
        """
        Parse provided file
        """
        self.dictionary = self._decoder.decode()

    def mbsize(self):
        '''Returns the size in MB'''
        return self.rawsize() / (1024*1024)

    def gbsize(self):
        '''Returns the size in GB'''
        return self.rawsize() / (1024*1024*1024)

    def name(self):
        '''Returns the name of the torrent, as specified in the info'''
        if 'name' in self.dictionary['info']:
            return self.dictionary['info']['name']

    def rawsize(self):
        '''Returns the size in bytes'''
        size = 0
        if 'files' in self.dictionary['info']:
            for ff in self.dictionary['info']['files']:
                size += ff['length']
        elif 'name' in self.dictionary['info']:
            size += self.dictionary['info']['length']
        return size
